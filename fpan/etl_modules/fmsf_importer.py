import csv
import copy
import json
import time
import uuid
import inspect
import logging
from datetime import datetime
from pathlib import Path

from django.contrib.gis.gdal import DataSource
from django.contrib.gis.db.models import Union
from django.db import connection
from django.db.models import Q
from django.db.utils import IntegrityError, ProgrammingError
from django.utils.translation import ugettext as _

import arches.app.tasks as tasks
import arches.app.utils.task_management as task_management
from arches.app.datatypes.datatypes import DataTypeFactory
from arches.app.models.concept import Concept
from arches.app.models.models import GraphModel, Node, NodeGroup, ETLModule
from arches.app.models.tile import Tile
from arches.app.models.resource import Resource
from arches.app.utils.betterJSONSerializer import JSONSerializer
from arches.app.utils.index_database import index_resources_by_transaction
from arches.app.etl_modules.base_import_module import BaseImportModule

from hms.models import ManagementArea

logger = logging.getLogger(__name__)

details = {
    "etlmoduleid": "3b19a76a-0b09-450e-bee1-bbaccb0960bb",
    "name": "FMSF Data Importer",
    "description": "Loads resource data from a JSON source",
    "etl_type": "import",
    "component": "views/components/etl_modules/fmsf-importer",
    "componentname": "fmsf-importer",
    "modulename": "fmsf_importer.py",
    "classname": "FMSFImporter",
    "config": {"circleColor": "#ff77cc", "bgColor": "#cc2266", "show": False},
    "icon": "fa fa-upload",
    "slug": "fmsf-importer"
}

field_maps = {
    "Archaeological Site": {
        "FMSF ID": [
            {"field": "SITEID", "source": "shp"},
        ],
        "FMSF Name": [
            {"field": "SITENAME", "source": "shp"},
        ],
        "Geospatial Coordinates": [
            {"field": "geom", "source": "shp"},
        ],
        "Human Remains": [
            {"field": "HUMANREMNS", "source": "shp"},
        ],
        "National Register List Date": [
            {"field": "D_NRLISTED", "source": "shp"},
        ],
        "Ownership": [
            {"field": "Ownership", "source": "csv"},
        ],
        "Plot Type": [
            {"field": "PLOTTYPE", "source": "shp"},
        ],
        "SHPO Evaluation": [
            {"field": "SHPOEVAL", "source": "shp"},
        ],
        "Site Culture": [
            {"field": "CULTURE1", "source": "shp"},
            {"field": "CULTURE2", "source": "shp"},
            {"field": "CULTURE3", "source": "shp"},
            {"field": "CULTURE4", "source": "shp"},
            {"field": "CULTURE5", "source": "shp"},
            {"field": "CULTURE6", "source": "shp"},
            {"field": "CULTURE7", "source": "shp"},
            {"field": "CULTURE8", "source": "shp"},
        ],
        "Site Type": [
            {"field": "SITETYPE1", "source": "shp"},
            {"field": "SITETYPE2", "source": "shp"},
            {"field": "SITETYPE3", "source": "shp"},
            {"field": "SITETYPE4", "source": "shp"},
            {"field": "SITETYPE5", "source": "shp"},
            {"field": "SITETYPE6", "source": "shp"}
        ],
        "Survey Evaluation": [
            {"field": "SURVEVAL", "source": "shp"},
        ],
        "Survey Number": [
            {"field": "SURVEYNUM", "source": "shp"},
        ]
    },
    "Historic Cemetery": {
        "FMSF ID": [
            {"field": "SITEID", "source": "shp"}
        ],
        "FMSF Name": [
            {"field": "SITENAME", "source": "shp"}
        ],
        "Geospatial Coordinates": [
            {"field": "geom", "source": "shp"}
        ],
        "Cemetery Status": [
            {"field": "STATUS", "source": "shp"}
        ],
        "Cemetery Type": [
            {"field": "CEMTYPE1", "source": "shp"},
            {"field": "CEMTYPE2", "source": "shp"}
        ],
        "Ethnic Groups Interred": [
            {"field": "ETHNICGRP1", "source": "shp"},
            {"field": "ETHNICGRP2", "source": "shp"},
            {"field": "ETHNICGRP3", "source": "shp"},
            {"field": "ETHNICGRP4", "source": "shp"},
        ],
        "National Register List Date": [
            {"field": "D_NRLISTED", "source": "shp"}
        ],
        "Ownership": [
            {"field": "Ownership", "source": "csv"}
        ],
        "Plot Type": [
            {"field": "PLOTTYPE", "source": "shp"}
        ],
        "SHPO Evaluation": [
            {"field": "SHPOEVAL", "source": "shp"}
        ],
        "Survey Number": [
            {"field": "SURVEYNUM", "source": "shp"}
        ]
    },
    "Historic Structure": {
        "FMSF ID": [
            {"field": "SITEID", "source": "shp"}
        ],
        "FMSF Name": [
            {"field": "SITENAME", "source": "shp"}
        ],
        "Geospatial Coordinates": [
            {"field": "geom", "source": "shp"}
        ],
        "Architect": [
            {"field": "ARCHITECT", "source": "shp"}
        ],
        "Exterior Fabric": [
            {"field": "EXTFABRIC1", "source": "shp"},
            {"field": "EXTFABRIC2", "source": "shp"},
            {"field": "EXTFABRIC3", "source": "shp"},
            {"field": "EXTFABRIC4", "source": "shp"}
        ],
        "Exterior Plan": [
            {"field": "EXTPLAN", "source": "shp"}
        ],
        "National Register List Date": [
            {"field": "D_NRLISTED", "source": "shp"}
        ],
        "Ownership": [
            {"field": "Ownership", "source": "csv"}
        ],
        "Plot Method": [
            {"field": "PLOTMTHD", "source": "shp"}
        ],
        "SHPO Evaluation": [
            {"field": "SHPOEVAL", "source": "shp"}
        ],
        "Structural System": [
            {"field": "STRUCSYS1", "source": "shp"},
            {"field": "STRUCSYS2", "source": "shp"},
            {"field": "STRUCSYS3", "source": "shp"}
        ],
        "Structure Use": [
            {"field": "STRUCUSE1", "source": "shp"},
            {"field": "STRUCUSE2", "source": "shp"},
            {"field": "STRUCUSE3", "source": "shp"}
        ],
        "Style": [
            {"field": "STYLE", "source": "shp"}
        ],
        "Survey Evaluation": [
            {"field": "SURVEVAL", "source": "shp"}
        ],
        "Survey Evaluation (District)": [
            {"field": "SURVDIST", "source": "shp"}
        ],
        "Survey Number": [
            {"field": "SURVEYNUM", "source": "shp"}
        ]
    }
}

specials = {
    "Ethnic Groups Interred": {
        "Unspecified by surveyor": "Unspecified by Surveyor"
    },
    "Cemetery Status": {
        "Unspecified by surveyor": "Unspecified by Surveyor"
    },
    "Plot Method": {
        "d": "D"
    },
    "Ownership": {
        'CITY': "City",
        'COUN': "County",
        'STAT': "State",
        'FEDE': "Federal",
        'PULO': "Local government",
        'PRIV': "Private-individual",
        'CORP': "Private-corporate-for profit",
        'CONP': "Private-corporate-nonprofit",
        'FORE': "Foreign",
        'NAAM': "Native American",
        'MULT': "Multiple categories of ownership",
        'UNSP': "Unspecified by Surveyor",
        'PUUN': "Public-unspecified",
        'PRUN': "Private-unspecified",
        'OTHR': "Other",
        'UNKN': "Unknown"
    }
}

class ETLOperationResult():

    def __init__(self, operation, success=True, message="", data={}):
        self.operation = operation
        self.start_time = time.time()
        self.success = success
        self.message = message
        self.data = data
        self.seconds = 0

    def __str__(self):
        return str(self.as_dict())
    
    def stop_timer(self):
        self.seconds = round(time.time() - self.start_time, 2)

    def as_dict(self):

        return {
            "operation": self.operation,
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "seconds": self.seconds,
        }

class FMSFImporter(BaseImportModule):
    def __init__(self, request=None):
        self.request = request if request else None
        self.userid = request.user.id if request else None
        self.loadid = request.POST.get("load_id") if request else None
        self.moduleid = request.POST.get("module") if request else None
        self.datatype_factory = DataTypeFactory()

        self.features = []
        self.new_features = []
        self.existing_features = []
        self.tiles = []
        self.fmsf_resources = []

        self.csv_filename_lookup = {
            "AR.csv": {
                "resource_type": "Archaeological Site",
                "shp_name": "FloridaSites.shp",
            },
            "CM.csv": {
                "resource_type": "Historic Cemetery",
                "shp_name": "HistoricalCemeteries.shp",
            },
            "SS.csv": {
                "resource_type": "Historic Structure",
                "shp_name": "FloridaStructures.shp",
            },
        }

        self.blank_tile_lookup = {}
        self.concept_lookups = {}
        self.node_lookup = {}
        self.nodegroup_lookup = {}
        self.resource_lookup = {}
        self.special_label_lookups = specials

    def set_resource_type(self, resource_type):
        self.graph = GraphModel.objects.get(name=resource_type)
        self.field_map = field_maps[resource_type]

        self.resource_type = resource_type
        self.set_resource_lookup()

    def set_resource_type_from_csv(self):
        rt = self.csv_filename_lookup[self.csv_file.name]['resource_type']
        self.set_resource_type(rt)

    def set_resource_lookup(self):

        resources = Resource.objects.filter(graph=self.graph)
        for resource in resources:
            try:
                siteid = resource.get_node_values("FMSF ID")[0]
            except IndexError:
                logger.warn(f"orphan resource: {resource.pk} has no FMSF ID")
                continue
            self.resource_lookup[siteid] = resource

    def _read_csv(self):

        data = {}
        with open(self.csv_file, "r") as in_csv:
            reader = csv.DictReader(in_csv)
            for row in reader:
                siteid = row['SiteID'].rstrip()
                data[siteid] = data.get(siteid, []) + [row]
        self.csv_data = data

    def get_value_from_csv(self, siteid, field_name):
        """ the trick here is that the CSV data will have multiple rows per
        siteid (site forms submitted over the years. For now, just iterate these
        rows and return the last row that has a non-empty value for this field. """

        value = None
        if siteid in self.csv_data:
            for i in self.csv_data[siteid]:
                form_value = i.get(field_name, "")
                if form_value.rstrip() != "":
                    value = form_value

        return value

    def apply_historical_structures_filter(self):

        def _feature_is_lighthouse(feature):
            vals = [feature.get(f"STRUCUSE{i}") for i in [1,2,3]]
            return any([i for i in vals if i and i.lower() == "lighthouse"])

        def _feature_is_destroyed(feature):
            return feature.get("DESTROYED") == "YES"

        result = ETLOperationResult(inspect.currentframe().f_code.co_name)

        lighthouse_list, geom_list = [], []
        for feature in self.new_features:
            # first skip structure marked as destroyed
            if _feature_is_destroyed(feature):
                continue
            # now, collect sites that are (or were) lighthouses
            siteid = feature.get("SITEID").rstrip()
            if _feature_is_lighthouse(feature):
                lighthouse_list.append(siteid)
            # for all others, collect geometry to filter by location
            else:
                geom_list.append((siteid, feature.geom.wkt))

        # CREATE AND RUN GEOMETRY FILTER AGAINST SELECTED MANAGEMENT AREAS
        logger.debug("unioning Management Areas")
        nr_qry = Q(load_id="nr-districts-Sept2022")
        sp_qry = Q(management_agency__name="Florida State Parks")
        filter_areas = ManagementArea.objects.filter(nr_qry | sp_qry)
        union_results = filter_areas.aggregate(Union('geom'))
        union_geom = union_results['geom__union']
        logger.debug("union geom created")

        values_str = ", ".join([f"('{i[0]}', '{i[1]}')" for i in geom_list])
        with connection.cursor() as cursor:
            logger.debug(f"generate table of structure geoms. geom ct: {len(geom_list)}")
            cursor.execute(
                f"""
                DROP TABLE IF EXISTS historic_structures_tmp;
                CREATE TABLE historic_structures_tmp (siteid varchar, geom geometry);
                INSERT INTO historic_structures_tmp VALUES {values_str};
                """
            )
            logger.debug(f"performing intersect operation")
            cursor.execute(
                f"""SELECT siteid, geom FROM historic_structures_tmp
                    WHERE ST_Intersects(geom, '{union_geom.wkt}');"""
            )
            rows = cursor.fetchall()
            geom_matches = [i[0] for i in rows]
            cursor.execute(
                f"""DROP TABLE IF EXISTS historic_structures_tmp;"""
            )

        logger.debug(f"intersect complete, {len(geom_matches)} matching features.")
        use_list = set(lighthouse_list + geom_matches)

        original_ct = len(self.new_features)
        self.new_features = [i for i in self.new_features if i.get("SITEID") in use_list]

        result.message = f"{len(self.new_features)} out of {original_ct} left after structure filter"
        result.data = {
            "original features": original_ct,
            "post-filter features": len(self.new_features),
        }
        result.stop_timer()
        return result

    def validate_shp_fields(self, layer):

        shp_fields = []
        for fieldset in self.field_map.values():
            for item in fieldset:
                if item['source'] == "shp" and not item['field'] == "geom":
                    shp_fields.append(item['field'])

        return [i for i in shp_fields if not i in layer.fields]

    def read_features_from_shapefile(self):

        ds = DataSource(self.shp_file)
        lyr = ds[0]

        result = ETLOperationResult(inspect.currentframe().f_code.co_name)

        for feature in lyr:
            self.features.append(feature)
            siteid = feature.get("SITEID").rstrip()
            if siteid in self.resource_lookup:
                self.existing_features.append(feature)
            else:
                self.new_features.append(feature)

        result.data = {
            "new features": len(self.new_features),
            "existing features": len(self.existing_features),
        }
        result.stop_timer()
        return result

    def lookup_labelid_from_label(self, value, node):
        """ This is a pretty simplistic approach, which should work for FMSF but 
        may not with a nested RDM collection. """

        collectionid = node.config['rdmCollection']
        if not collectionid in self.concept_lookups:
            concepts = Concept().get_child_collections(node.config['rdmCollection'])
            self.concept_lookups[collectionid] = concepts

        # Allow some special handling of certan known typos in the FMSF
        if node.name in self.special_label_lookups:
            if value in self.special_label_lookups[node.name]:
                value = self.special_label_lookups[node.name][value]

        labelid = None
        for triple in self.concept_lookups[collectionid]:
            if triple[1] == value:
                labelid = triple[2]
                break
        if labelid is None:
            logger.warn(f"Invalid prefLabel {value} for node {node.name} with collection {node.config['rdmCollection']}")
        return labelid

    def start(self, request=None):

        result = ETLOperationResult(inspect.currentframe().f_code.co_name)
        if self.loadid is None:
            self.loadid = str(uuid.uuid4())
        if self.moduleid is None:
            self.moduleid = ETLModule.objects.get(classname=self.__class__.__name__).pk
        if self.userid is None:
            self.userid = 1
        if request is not None:
            graphid = request.POST.get("graphid")
            csv_mapping = request.POST.get("fieldMapping")
            mapping_details = {"mapping": json.loads(csv_mapping), "graph": graphid}
        else:
            mapping_details = {}
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO load_event (loadid, complete, status, etl_module_id, load_details, load_start_time, user_id) VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (self.loadid, False, "running", self.moduleid, json.dumps(mapping_details), datetime.now(), self.userid),
            )

        result.message = f"etl started with loadid: {self.loadid}"
        result.data = {"loadid": self.loadid},
        result.stop_timer()
        return result

    def validate_files(self, file_dir):

        result = ETLOperationResult(
            inspect.currentframe().f_code.co_name,
            message="all files ok"
        )
        csv = Path()
        for i in Path(file_dir).glob("*.csv"):
            csv = i
            break

        if csv.name in self.csv_filename_lookup:
            self.csv_file = csv
            self.shp_file = Path(csv.parent, self.csv_filename_lookup[csv.name]['shp_name'])
            if not self.shp_file.exists():
                result.success = False
                result.message = f"Shapefile is missing. Expected path: {self.shp_file}"
            self.set_resource_type_from_csv()
        else:
            result.success = False
            result.message = f"Invalid CSV file: {csv}. Must be one of {self.csv_filename_lookup.keys()}"

        if result.success is True:
            try:
                ds = DataSource(self.shp_file)
                lyr = ds[0]
            except Exception as e:
                result.success = False
                result.message = str(e)

            if result.success is True:
                missing = self.validate_shp_fields(lyr)
                if len(missing) > 0:
                    result.success = False
                    result.message = f"Shapefile is missing these fields: {', '.join(missing)}"
                    result.data = {"fields": missing}

        result.stop_timer()
        return result

    def generate_load_data(self, truncate=None):

        result = ETLOperationResult(inspect.currentframe().f_code.co_name)

        self.tiles = []
        self.fmsf_resources = []

        # try:
        start = time.time()
        current_percent = 0
        for n, feature in enumerate(self.new_features, start=1):
            percent = int(n/len(self.new_features) * 100)
            if percent != current_percent:
                if percent == 1:
                    elapsed = time.time() - start
                    est = int(elapsed * 100)
                    logger.debug(f"estimated completion: {round(est/60, 2)} min")
                if percent == 100:
                    logger.debug(percent)
                elif percent % 5 == 0:
                    logger.debug(percent)
                current_percent = percent

            res = FMSFResource().from_shp_feature(feature)
            if res.siteid in self.resource_lookup:
                res.resource = self.resource_lookup[res.siteid]
                res.resourceid = str(res.resource.pk)
            else:
                res.resource = None
                res.resourceid = uuid.uuid4()

            tiles = res.generate_tiles(self)

            self.tiles += tiles
            self.fmsf_resources.append(res)

            if n == truncate:
                break

        # except Exception as e:
        #     success = False
        #     message = str(e)

        result.message = f"resources: {len(self.fmsf_resources)}, tiles: {len(self.tiles)}"
        result.data = {"resource_ct": len(self.fmsf_resources), "tile_ct": len(self.tiles)}
        result.stop_timer()
        return result

    def write_data_to_load_staging(self):

        result = ETLOperationResult(inspect.currentframe().f_code.co_name)
        try:
            with connection.cursor() as cursor:
                for tile in self.tiles:
                    cursor.execute(
                        """
                        INSERT INTO load_staging (
                            nodegroupid,
                            legacyid,
                            resourceid,
                            tileid,
                            parenttileid,
                            value,
                            loadid,
                            nodegroup_depth,
                            source_description,
                            passes_validation
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        tile,
                    )

                cursor.execute("""CALL __arches_check_tile_cardinality_violation_for_load(%s)""", [self.loadid])
            result.message = f"{len(self.tiles)} tiles written to load_staging table"
        except Exception as e:
            result.success = False
            result.message = str(e)

        result.stop_timer()
        return result

    def write_tiles_from_load_staging(self):

        result = ETLOperationResult(inspect.currentframe().f_code.co_name)
        
        try:
            with connection.cursor() as cursor:
                # cursor.execute("""CALL __arches_prepare_bulk_load();""")
                cursor.execute("""ALTER TABLE tiles disable trigger __arches_check_excess_tiles_trigger;""")
                cursor.execute("""ALTER TABLE tiles disable trigger __arches_trg_update_spatial_attributes;""")
            with connection.cursor() as cursor:
                cursor.execute("""SELECT * FROM __arches_staging_to_tile(%s)""", [self.loadid])
                row = cursor.fetchall()
            result.message = f"all tiles written to tile table"
            if row[0][0]:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """UPDATE load_event SET (status, load_end_time) = (%s, %s) WHERE loadid = %s""",
                        ("completed", datetime.now(), self.loadid),
                    )
            else:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """UPDATE load_event SET status = %s, load_end_time = %s WHERE loadid = %s""",
                        ("failed", datetime.now(), self.loadid),
                    )
                result.success = False
                result.message = "No rows resulted from the write process"
        except (IntegrityError, ProgrammingError) as e:
            with connection.cursor() as cursor:
                cursor.execute(
                    """UPDATE load_event SET status = %s, load_end_time = %s WHERE loadid = %s""",
                    ("failed", datetime.now(), self.loadid),
                )
            result.success = False
            result.message = str(e)
        finally:
            with connection.cursor() as cursor:
                # cursor.execute("""CALL __arches_complete_bulk_load();""")
                cursor.execute("""ALTER TABLE tiles enable trigger __arches_check_excess_tiles_trigger;""")
                cursor.execute("""ALTER TABLE tiles enable trigger __arches_trg_update_spatial_attributes;""")
            pass

        result.stop_timer()
        return result

    def finalize_indexing(self):

        result = ETLOperationResult(inspect.currentframe().f_code.co_name)
        try:
            index_resources_by_transaction(self.loadid, quiet=True, use_multiprocessing=False)
            with connection.cursor() as cursor:
                cursor.execute(f"REFRESH MATERIALIZED VIEW mv_geojson_geoms;")
            with connection.cursor() as cursor:
                cursor.execute(
                    """UPDATE load_event SET (status, indexed_time, complete, successful) = (%s, %s, %s, %s) WHERE loadid = %s""",
                    ("indexed", datetime.now(), True, True, self.loadid),
                )
            result.message = "resources indexed and materialized view refreshed"
        except Exception as e:
            result.success = False
            result.message = str(e)

        result.stop_timer()
        return result


    def import_via_cli(self, **kwargs):

        elapsed = 0

        truncate = kwargs.get("truncate")
        if truncate is not None:
            truncate = int(truncate)
        file_dir = kwargs.get("file_dir")
        if file_dir is None:
            raise Exception("file_dir must be provided")

        result = self.validate_files(file_dir)
        logger.info(result)
        elapsed += result.seconds
        if result.success is False:
            raise Exception(result.message)

        result = self.start()
        logger.info(result)
        elapsed += result.seconds

        result = self.read_features_from_shapefile()
        logger.info(result)
        elapsed += result.seconds
        if len(self.new_features) == 0:
            logger.info("no new features to write")
            exit()

        if self.resource_type == "Historic Structure":
            result = self.apply_historical_structures_filter()
            logger.info(result)
            elapsed += result.seconds
            if result.success is False:
                raise Exception(result.message)

        self._read_csv()

        result = self.generate_load_data(truncate=truncate)
        logger.info(result)
        elapsed += result.seconds
        if result.success is False:
            raise Exception(result.message)

        result = self.write_data_to_load_staging()
        logger.info(result)
        elapsed += result.seconds
        if result.success is False:
            raise Exception(result.message)

        result = self.write_tiles_from_load_staging()
        logger.info(result)
        elapsed += result.seconds
        if result.success is False:
            raise Exception(result.message)

        result = self.finalize_indexing()
        logger.info(result)
        elapsed += result.seconds
        if result.success is False:
            raise Exception(result.message)

        logger.info(f"total time: {elapsed} seconds")

    def get_node(self, node_name):
        node = self.node_lookup.get(node_name)
        if node is None:
            node = Node.objects.filter(graph=self.graph, name=node_name).exclude(datatype="semantic")
            if len(node) != 1:
                raise Exception(f"problematic node name for this graph: {node_name}")
            else:
                node = node[0]
            self.node_lookup[node_name] = node
        return node

    def get_blank_tile(self, nodegroupid):

        blank_tile = self.blank_tile_lookup.get(nodegroupid)
        if blank_tile is None:
            blank_tile = {}
            with connection.cursor() as cursor:
                cursor.execute("""SELECT nodeid FROM nodes WHERE datatype <> 'semantic' AND nodegroupid = %s;""", [nodegroupid])
                for row in cursor.fetchall():
                    (nodeid,) = row
                    blank_tile[str(nodeid)] = None
            self.blank_tile_lookup[nodegroupid] = blank_tile
        return blank_tile

    def get_nodegroup(self, nodegroupid):
        nodegroup = self.nodegroup_lookup.get(nodegroupid)
        if nodegroup is None:
            nodegroup = NodeGroup.objects.get(pk=nodegroupid)
            self.nodegroup_lookup[nodegroupid] = nodegroup
        return nodegroup


class FMSFResource():

    def __init__(self):

        self.siteid = None
        self.feature = None
        self.parent_tile_lookup = {}
    
    def from_shp_feature(self, feature):

        self.siteid = feature.get("SITEID")
        if not self.siteid:
            raise Exception("bad shapefile feature: missing or empty SITEID field")
        self.feature = feature
        return self

    def management_areas_from_geom(self, geojson):

        with connection.cursor() as cursor:
            cursor.execute(
                f'''SELECT id FROM hms_managementarea
                        WHERE ST_Intersects(ST_GeomFromGeoJSON('{geojson}'), hms_managementarea.geom);'''
            )
            rows = cursor.fetchall()
        pks = [i[0] for i in rows if len(i) > 0]
        return ManagementArea.objects.filter(pk__in=pks)

    def generate_management_area_node_objs(self, management_areas, importer):

        values_dict = {
            "FPAN Region": [],
            "County": [],
            "Management Area": [],
            "Management Agency": [],
        }
        for ma in management_areas:
            if ma.category.name == "FPAN Region":
                values_dict["FPAN Region"].append(ma)
            elif ma.category.name == "County":
                values_dict["County"].append(ma)
            else:
                values_dict["Management Area"].append(ma)
                values_dict["Management Agency"].append(ma.management_agency)

        node_objs = []
        nodegroupid = None
        for node_name, value in values_dict.items():
            node = importer.get_node(node_name)
            if nodegroupid is None:
                nodegroupid = str(node.nodegroup_id)
            node_objs.append({
                str(node.nodeid): {
                    "value": [str(i.pk) for i in value],
                    "valid": True,
                    "source": [str(i.pk) for i in value],
                    "notes": "",
                    "datatype": node.datatype,
                }
            })
        return nodegroupid, node_objs

    def generate_tiles(self, importer: FMSFImporter):

        dict_by_nodegroup = {}
        management_areas = []
        for node_name, fieldset in importer.field_map.items():
            node = importer.get_node(node_name)
            node_config = node.config if node.config else {}
            datatype_instance = importer.datatype_factory.get_instance(node.datatype)
            nodegroupid = str(node.nodegroup_id)
            if node.datatype in ['concept-list', 'concept']:
                values = []
                source_values = []
                for field in fieldset:
                    value = None
                    if field['source'] == "shp":
                        value = self.feature.get(field['field'])
                    elif field['source'] == "csv":
                        value = importer.get_value_from_csv(self.siteid, field['field'])
                    if value is not None:
                        source_values.append(value)
                        labelid = importer.lookup_labelid_from_label(value, node)
                        if labelid is not None:
                            values.append(labelid)
                if len(values) > 1 and node.datatype == "concept":
                    raise Exception(f"concept node can't fit multiple values: {values}")
                source_value = ",".join(values)
                value = datatype_instance.transform_value_for_tile(source_value, **node_config)
            elif node.datatype in ['date']:
                source_value = self.feature.get(fieldset[0]['field'])
                if source_value is not None:
                    source_value = str(source_value)
                value = datatype_instance.transform_value_for_tile(source_value, **node_config)
            else:
                if fieldset[0]['field'] == "geom":
                    geom = self.feature.geom
                    with connection.cursor() as cursor:
                        cursor.execute(f"SELECT ST_AsGeoJSON( ST_RemoveRepeatedPoints('{geom.wkt}'));")
                        geojson = cursor.fetchone()[0]
                    source_value = geojson
                    # also, run spatial intersection to find overlapping management areas
                    management_areas += self.management_areas_from_geom(geojson)
                else:
                    source_value = self.feature.get(fieldset[0]['field'])
                value = datatype_instance.transform_value_for_tile(source_value, **node_config)
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
            dict_by_nodegroup[nodegroupid] = dict_by_nodegroup.get(nodegroupid, []) + [node_obj]

        # generate tiles for the management area nodegroup
        ma_nodegroupid, ma_node_objs = self.generate_management_area_node_objs(management_areas, importer)
        dict_by_nodegroup[ma_nodegroupid] = ma_node_objs

        tiles = []
        for nid in dict_by_nodegroup:
            ng = importer.get_nodegroup(nid)
            if ng.parentnodegroup_id is not None:
                pt = self.parent_tile_lookup.get(ng.parentnodegroup_id)

                # if this is the first time the parent tile has been encountered for
                # this resource, create it and add a blank tile for it.
                if pt is None:
                    pt = Tile().get_blank_tile(nodegroupid, resourceid=self.resourceid)
                    pt.tileid = uuid.uuid4()
                    self.parent_tile_lookup[ng.parentnodegroup_id] = pt
                    tiles.append((
                        ng.parentnodegroup_id,
                        self.siteid,        # legacyid
                        self.resourceid,    # resourceid
                        pt.tileid,
                        None,
                        None,
                        importer.loadid,
                        0,
                        importer.csv_file.name,
                        True,
                    ))

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
                self.siteid,        # legacyid
                self.resourceid,    # resourceid
                tileid,
                parenttileid,
                tile_value_json,
                importer.loadid,
                nodegroup_depth,
                importer.csv_file.name,
                passes_validation,
            )
            tiles.append(row)

        return tiles
