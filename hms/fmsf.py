from typing import Union, TYPE_CHECKING
import logging

from arches.app.models.models import Node
from arches.app.models.resource import Resource
from arches.app.models.tile import Tile

import copy
import uuid

from django.contrib.gis.gdal.feature import Feature
from django.db import connection

from arches.app.utils.betterJSONSerializer import JSONSerializer

if TYPE_CHECKING:
    from fpan.etl_modules.fmsf_importer import FMSFImporter

logger = logging.getLogger(__name__)


# class FMSFResource:
#     """A wrapper class around an Arches resource that helps manage FMSF content"""

#     instance: Resource
#     siteid: Union[str, None]

#     def __init__(self, resourceid: str):

#         self.instance = Resource.objects.get(pk=resourceid)
#         self.siteid = self._get_siteid()

#     def _get_siteid(self) -> Union[str, None]:

#         node = Node.objects.get(name="FMSF ID", graph=self.instance.graph)
#         tiles = Tile.objects.filter(
#             resourceinstance_id=self.instance.pk, nodegroup=node.nodegroup
#         )
#         siteid = None
#         for t in tiles:
#             if t.data and str(node.pk) in t.data:
#                 siteid = t.data[str(node.pk)]["en"]["value"]
#         return siteid


class FMSFResource:
    siteid: Union[str, None]
    resource: Union[Resource, None]
    resourceid: str
    feature: Feature
    parent_tile_lookup: dict = {}

    @staticmethod
    def from_shp_feature(feature: Feature) -> "FMSFResource":

        siteid = feature.get("SITEID")
        if not siteid:
            raise Exception("bad shapefile feature: missing or empty SITEID field")
        res = FMSFResource()
        res.siteid = siteid
        res.feature = feature
        return res

    @staticmethod
    def from_arches(resourceid: str):

        res = FMSFResource()
        res.resource = Resource.objects.get(pk=resourceid)
        node = Node.objects.get(name="FMSF ID", graph=res.resource.graph)
        tiles = Tile.objects.filter(
            resourceinstance_id=resourceid,
            nodegroup=node.nodegroup,
            data__has_key=str(node.pk),
        )
        for t in tiles:
            if t.data:
                res.siteid = t.data[str(node.pk)]["en"]["value"]
        return res

    def generate_tiles(self, importer: "FMSFImporter"):

        dict_by_nodegroup = {}
        for node_name, fieldset in importer.field_map.items():
            node = importer.get_node(node_name)
            node_config = node.config if node.config else {}
            datatype_instance = importer.datatype_factory.get_instance(node.datatype)
            if node.nodegroup is None:
                continue
            nodegroupid = str(node.nodegroup.pk)
            if node.datatype in ["concept-list", "concept"]:
                values = []
                source_values = []
                for field in fieldset:
                    value = None
                    if field["source"] == "shp":
                        value = self.feature.get(field["field"])
                    elif field["source"] == "csv":
                        value = importer.get_value_from_csv(self.siteid, field["field"])
                    if value is not None:
                        source_values.append(value)
                        labelid = importer.lookup_labelid_from_label(value, node)
                        if labelid is not None:
                            values.append(labelid)
                if len(values) > 1 and node.datatype == "concept":
                    raise Exception(f"concept node can't fit multiple values: {values}")
                source_value = ",".join(values)
                value = datatype_instance.transform_value_for_tile(
                    source_value, **node_config
                )
            elif node.datatype in ["date"]:
                source_value = self.feature.get(fieldset[0]["field"])
                if source_value is not None:
                    source_value = str(source_value)
                else:
                    continue
                value = datatype_instance.transform_value_for_tile(
                    source_value, **node_config
                )
            else:
                if fieldset[0]["field"] == "geom":
                    geom = self.feature.geom
                    with connection.cursor() as cursor:
                        cursor.execute(
                            f"SELECT ST_AsGeoJSON( ST_RemoveRepeatedPoints( ST_MakeValid('{geom.wkt}')));"
                        )
                        result = cursor.fetchone()
                        if not result:
                            logger.warning("Error sanitizing geometry for tile.")
                            continue
                        geojson = result[0]
                    source_value = geojson
                else:
                    source_value = self.feature.get(fieldset[0]["field"])
                value = datatype_instance.transform_value_for_tile(
                    source_value, **node_config
                )
            valid = True
            error_message = ""
            node_obj = {
                str(node.nodeid): {
                    "value": value,
                    "valid": valid,
                    "source": source_value,
                    "notes": error_message,
                    "datatype": node.datatype,
                }
            }
            dict_by_nodegroup[nodegroupid] = dict_by_nodegroup.get(nodegroupid, []) + [
                node_obj
            ]

        tiles = []
        for nid in dict_by_nodegroup:
            ng = importer.get_nodegroup(nid)
            if ng.parentnodegroup is not None:
                parentnodegroup_id = str(ng.parentnodegroup.pk)
                pt = self.parent_tile_lookup.get(parentnodegroup_id)

                # if this is the first time the parent tile has been encountered for
                # this resource, create it and add a blank tile for it.
                if pt is None:
                    pt = Tile().get_blank_tile(nid, resourceid=self.resourceid)
                    pt.tileid = uuid.uuid4()
                    self.parent_tile_lookup[parentnodegroup_id] = pt
                    tiles.append(
                        (
                            parentnodegroup_id,
                            self.siteid,  # legacyid
                            self.resourceid,  # resourceid
                            pt.tileid,
                            None,
                            None,
                            importer.loadid,
                            0,
                            importer.resource_csv.name,
                            True,
                        )
                    )

                # now set the appropriate values for the business data tile
                parenttileid = pt.tileid
                nodegroup_depth = 1
            else:
                parenttileid = None
                nodegroup_depth = 0

            tile_data = copy.deepcopy(importer.get_blank_tile(nid))
            passes_validation = True
            for node in dict_by_nodegroup[nid]:
                for key in node:
                    tile_data[key] = node[key]
                    if node[key]["valid"] is False:
                        passes_validation = False

            tileid = uuid.uuid4()
            tile_value_json = JSONSerializer().serialize(tile_data)

            row = (
                nid,
                self.siteid,  # legacyid
                self.resourceid,  # resourceid
                tileid,
                parenttileid,
                tile_value_json,
                importer.loadid,
                nodegroup_depth,
                importer.resource_csv.name,
                passes_validation,
            )
            tiles.append(row)

        return tiles
