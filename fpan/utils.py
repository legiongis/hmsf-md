import json
import time
import logging

from django.conf import settings
from django.db import connection

from arches.app.models.models import ResourceInstance, Node
from arches.app.models.tile import Tile

from hms.models import ManagementArea, ManagementAgency

logger = logging.getLogger(__name__)

class SpatialJoin():

    def __init__(self):

        self.node_lookup = settings.SPATIAL_JOIN_GRAPHID_LOOKUP
        self.valid_management_area_vals = [i.concept_value_id for i in ManagementArea.objects.all()]
        self.valid_management_agency_vals = [i.concept_value_id for i in ManagementAgency.objects.all()]

    def update_resource(self, resourceinstance):

        areas_pks = self.get_areas_for_resourceinstance(resourceinstance)
        for area in ManagementArea.objects.filter(pk__in=areas_pks):
            self.apply_management_area_attributes(resourceinstance, area)

    def join_management_area_to_resources(self, area):

        resids = self.get_resources_for_area(area)
        for resinstance in ResourceInstance.objects.filter(pk__in=resids):
            self.apply_management_area_attributes(resinstance, area)

    def get_areas_for_resourceinstance(self, resourceinstance):

        with connection.cursor() as cursor:
            cursor.execute(
                '''SELECT id FROM hms_managementarea
                        WHERE ST_Intersects(
                            (SELECT ST_Transform(ST_Union(geom), 4326) FROM geojson_geometries WHERE resourceinstanceid = %s), hms_managementarea.geom);''',
                            (str(resourceinstance.pk), )
            )
            rows = cursor.fetchall()
        return [i[0] for i in rows if len(i) > 0]

    def get_resources_for_area(self, area):

        with connection.cursor() as cursor:
            cursor.execute(
                f'''SELECT resourceinstanceid FROM geojson_geometries
                        WHERE ST_Intersects( ST_GeomFromText( %s, 4326 ), ST_Transform(geojson_geometries.geom, 4326) );''',
                        (area.geom.wkt,)
            )
            rows = cursor.fetchall()
        return [str(i[0]) for i in rows if len(i) > 0]

    def apply_management_area_attributes(self, resourceinstance, area):

        g_name = resourceinstance.graph.name
        n_lookup = self.node_lookup[g_name]
        ng = self.node_lookup[g_name]['Nodegroup']
        try:
            tile = Tile.objects.get(nodegroup_id=ng, resourceinstance=resourceinstance)
        except Tile.DoesNotExist:
            tile = Tile().get_blank_tile(ng, resourceid=resourceinstance.pk)

        # set empty lists if the node value is None or nonexistent
        if not isinstance(tile.data.get(n_lookup['FPAN Region']), list):
            tile.data[n_lookup['FPAN Region']] = []
        if not isinstance(tile.data.get(n_lookup['County']), list):
            tile.data[n_lookup['County']] = []
        if not isinstance(tile.data.get(n_lookup['Management Area']), list):
            tile.data[n_lookup['Management Area']] = []
        if not isinstance(tile.data.get(n_lookup['Management Agency']), list):
            tile.data[n_lookup['Management Agency']] = []

        val = area.concept_value_id
        add_to_main = True
        # if management area has a category, check for where it should be added
        if area.category is not None:
            # add to region node in this case
            if area.category.name == "FPAN Region":
                add_to_main = False
                tile.data[n_lookup['FPAN Region']].append(val)
            # add to county node in this case
            elif area.category.name == "County":
                add_to_main = False
                tile.data[n_lookup['County']].append(val)
        # for all other cases, add to the main Management Area node
        if add_to_main is True:
            tile.data[n_lookup['Management Area']].append(val)
        # add the agency if available
        if area.management_agency is not None:
            tile.data[n_lookup['Management Agency']].append(area.management_agency.concept_value_id)

        # finalize with some QA/QC
        tile.data[n_lookup['FPAN Region']] = list(set(
            [i for i in tile.data[n_lookup['FPAN Region']] if i in self.valid_management_area_vals]
        ))
        tile.data[n_lookup['County']] = list(set(
            [i for i in tile.data[n_lookup['County']] if i in self.valid_management_area_vals]
        ))
        tile.data[n_lookup['Management Area']] = list(set(
            [i for i in tile.data[n_lookup['Management Area']] if i in self.valid_management_area_vals]
        ))
        tile.data[n_lookup['Management Agency']] = list(set(
            [i for i in tile.data[n_lookup['Management Agency']] if i in self.valid_management_agency_vals]
        ))

        tile.save()

def get_node_value(resource, node_name):
    """this just flattens the response from Resource().get_node_values()"""

    values = resource.get_node_values(node_name)
    if len(values) == 0:
        value = ""
    elif len(values) == 1:
        value = values[0]
    else:
        value = "; ".join(values)

    return value


class ETLOperationResult():

    def __init__(self, operation, loadid=None, success=True, message="", data={}):
        self.operation = operation
        self.loadid = loadid
        self.start_time = time.time()
        self.success = success
        self.message = message
        self.data = data
        self.seconds = 0

    def __str__(self):
        return str(self.serialize())
    
    def stop_timer(self):
        self.seconds = round(time.time() - self.start_time, 2)

    def log(self, logger, level='info'):
        level_lookup = {
            "critical": 50,
            "error": 40,
            "warn": 30,
            "info": 20,
            "debug": 10,
            "none": 0,
        }
        message = f"loadid: {self.loadid} | {self.message}"
        logger.log(level_lookup[level], message)

    def get_load_details(self):
        """
        returns this result's data in the desired format for insertion into
        the load_event table (column: load_details) - inserts self.message into
        the returned data.
        """
        details = dict(self.data)
        details['Message'] = self.message
        return json.dumps(details)

    def serialize(self):

        details = dict(self.data)
        details['Message'] = self.message

        return {
            "operation": self.operation,
            "success": self.success,
            "data": details,
        }
