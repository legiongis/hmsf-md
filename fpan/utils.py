import json
import time
import logging
from typing import TYPE_CHECKING
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.db import connection, transaction
from django.contrib.gis.db.models import Union
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon

from arches.app.models.resource import Resource
from arches.app.models.models import ResourceInstance, Node, Value
from arches.app.models.tile import Tile
from arches.app.utils.index_database import index_resources_using_singleprocessing

from hms.models import ManagementArea, ManagementAgency

logger = logging.getLogger(__name__)

class SpatialJoin():

    def __init__(self):

        self.node_lookup = settings.SPATIAL_JOIN_NODE_LOOKUP
        self.valid_management_area_vals = [i.concept_value_id for i in ManagementArea.objects.all()]
        self.valid_management_agency_vals = [i.concept_value_id for i in ManagementAgency.objects.all()]

        self.county_lookup = self.hydrate_county_lookup()

    def hydrate_county_lookup(self) -> dict:

        with open(Path(settings.APP_ROOT, "data", "county_lookup.json"), "r") as o:
            lookup = json.load(o)

        for entry in lookup.values():
            county_label = f"{entry['county']} County"
            county_value = Value.objects.get(
                value=county_label,
                language_id="en",
                valuetype_id="prefLabel",
            )
            entry['county_concept_value_id'] = str(county_value.pk)

            region_label = f"FPAN {entry['region']} Region"
            region_value = Value.objects.get(
                value__startswith=region_label,
                language_id="en",
                valuetype_id="prefLabel",
            )
            entry['region_concept_value_id'] = str(region_value.pk)

        return lookup

    def update_resource(self, resourceinstance, index: bool = True):

        # get list of areas to pull info from
        intersecting_areas = self.get_areas_for_resourceinstance(resourceinstance)

        for area in intersecting_areas:
            self.apply_management_area_attributes(resourceinstance, area)

        resource = Resource.objects.get(pk=resourceinstance.pk)
        self.apply_fpan_region_and_county_attributes(resource)

        if index:
            resource.index()

    def join_management_area_to_resources(self, area):

        logger.info(f"joining {area.name} to resources")

        # first find a list of all resource geometries that overlap this area
        with connection.cursor() as cursor:
            cursor.execute(
                '''SELECT resourceinstanceid FROM geojson_geometries
                        WHERE ST_Intersects(
                            ST_GeomFromText( %s, 4326 ),
                            ST_Transform(geojson_geometries.geom, 4326)
                        );''',
                        (area.geom.wkt,)
            )
            rows = cursor.fetchall()
        resids = [str(i[0]) for i in rows if len(i) > 0]

        resinstances = ResourceInstance.objects.filter(pk__in=resids).exclude(graph__name="Arches System Settings")
        logger.info(f"updating {resinstances.count()} resources overlapping this area")

        # iterate all intersecting resources and apply this area's attributes to them
        for resinstance in resinstances:
            self.apply_management_area_attributes(resinstance, area)

        # now index all resources
        resources = Resource.objects.filter(pk__in=resids).exclude(graph__name="Arches System Settings")
        logger.info(f"indexing {resources.count()} resources")
        index_resources_using_singleprocessing(resources=resources, quiet=True)

    def get_areas_for_resourceinstance(self, resourceinstance: ResourceInstance) -> list[ManagementArea]:
        start = datetime.now()
        geom_tile = Tile.objects.get(
            nodegroup_id__in=settings.SPATIAL_COORDINATES_NODEGROUPS_IDS,
            resourceinstance=resourceinstance
        )
        resource_geojson = None
        if geom_tile.data:
            geom_node = Node.objects.get(graph=resourceinstance.graph, datatype="geojson-feature-collection")
            try:
                resource_geojson = geom_tile.data[str(geom_node.pk)]
            except KeyError:
                logger.warning(f"no geojson node data in this resource: {resourceinstance.pk}")
                return []
        if not resource_geojson:
            print("no data in this geom tile")
            return []

        area_pks = []
        for feat in resource_geojson["features"]:
            geom_str = json.dumps(feat["geometry"])
            geom = GEOSGeometry(geom_str)
            pks = ManagementArea.objects.filter(geom__intersects=geom).values_list("pk", flat=True)
            area_pks += pks

        areas = list(ManagementArea.objects.exclude(
            category__name="FPAN Region"
        ).filter(pk__in=area_pks))

        print("elapsed:", datetime.now() - start)
        return areas

    def get_management_tile(self, resourceinstance: ResourceInstance) -> Tile:

        g_name = resourceinstance.graph.name
        ng = self.node_lookup[g_name]['nodegroupid']
        
        try:
            tile = Tile.objects.get(nodegroup_id=ng, resourceinstance=resourceinstance)
        except Tile.DoesNotExist:
            tile = Tile().get_blank_tile(ng, resourceid=resourceinstance.pk)

        if TYPE_CHECKING and not tile.data:
            return tile

        # set empty lists if the node value is None or nonexistent
        n_lookup = self.node_lookup[g_name]
        if not isinstance(tile.data.get(n_lookup['county_nodeid']), list):
            tile.data[n_lookup['county_nodeid']] = []
        if not isinstance(tile.data.get(n_lookup['region_nodeid']), list):
            tile.data[n_lookup['region_nodeid']] = []
        if not isinstance(tile.data.get(n_lookup['area_nodeid']), list):
            tile.data[n_lookup['area_nodeid']] = []
        if not isinstance(tile.data.get(n_lookup['agency_nodeid']), list):
            tile.data[n_lookup['agency_nodeid']] = []

        return tile

    def apply_management_area_attributes(self, resourceinstance: ResourceInstance, area: ManagementArea):
        """Takes in a resource instance and a ManagementArea, and attaches the ManagementArea
        and ManagementAgency concepts to the resource."""

        tile = self.get_management_tile(resourceinstance)

        if TYPE_CHECKING and not tile.data:
            return

        n_lookup = self.node_lookup[resourceinstance.graph.name]

        val = area.concept_value_id
        tile.data[n_lookup['area_nodeid']].append(val)

        # add the agency if available
        if area.management_agency is not None:
            tile.data[n_lookup['agency_nodeid']].append(area.management_agency.concept_value_id)

        # finalize with some QA/QC
        tile.data[n_lookup['area_nodeid']] = list(set(
            [i for i in tile.data[n_lookup['area_nodeid']] if i in self.valid_management_area_vals]
        ))
        tile.data[n_lookup['agency_nodeid']] = list(set(
            [i for i in tile.data[n_lookup['agency_nodeid']] if i in self.valid_management_agency_vals]
        ))

        tile.save(index=False)

    def apply_fpan_region_and_county_attributes(self, resourceinstance: ResourceInstance):

        tile = self.get_management_tile(resourceinstance)
        n_lookup = self.node_lookup[resourceinstance.graph.name]

        if TYPE_CHECKING and not tile.data:
            return

        siteid = get_node_value(resourceinstance, "FMSF ID")
        print(siteid)
        entry = self.county_lookup[siteid[:2]]
        print(entry)

        tile.data[n_lookup['county_nodeid']].append(entry['county_concept_value_id'])
        tile.data[n_lookup['region_nodeid']].append(entry['region_concept_value_id'])

        g_name = resourceinstance.graph.name
        n_lookup = self.node_lookup[g_name]
        # finalize with some QA/QC
        tile.data[n_lookup['area_nodeid']] = list(set(
            [i for i in tile.data[n_lookup['area_nodeid']] if i in self.valid_management_area_vals]
        ))
        tile.data[n_lookup['agency_nodeid']] = list(set(
            [i for i in tile.data[n_lookup['agency_nodeid']] if i in self.valid_management_agency_vals]
        ))

        tile.save(index=False)

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
