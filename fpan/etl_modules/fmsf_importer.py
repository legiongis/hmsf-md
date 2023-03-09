import gc
import os
import csv
import copy
import time
import uuid
import inspect
import logging
import zipfile
from datetime import datetime
from pathlib import Path

from django.contrib.gis.gdal import DataSource
from django.contrib.gis.db.models import Union
from django.db import connection
from django.db.models import Q
from django.db.utils import IntegrityError, ProgrammingError
from django.utils.translation import ugettext as _
from django.core.files import File
from django.core.files.storage import default_storage
from django.conf import settings

from arches.app.datatypes.datatypes import DataTypeFactory
from arches.app.etl_modules.base_import_module import BaseImportModule
from arches.app.models.concept import Concept
from arches.app.models.models import GraphModel, Node, NodeGroup, ETLModule
from arches.app.models.tile import Tile
from arches.app.models.resource import Resource
from arches.app.utils.betterJSONSerializer import JSONSerializer
from arches.app.utils.index_database import index_resources_by_transaction

from hms.models import ManagementArea
from fpan.tasks import run_sequence_as_task
from fpan.utils import ETLOperationResult

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
    "config": {"circleColor": "#ff77cc", "bgColor": "#cc2266", "show": True},
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

FILENAME_LOOKUP = {
    "Archaeological Site" : {
        "shp_name": "FloridaSites.shp",
        "csv_name": "AR.csv"
    },
    "Historic Cemetery": {
        "shp_name": "HistoricalCemeteries.shp",
        "csv_name": "CM.csv",
    },
    "Historic Structure": {
        "shp_name": "FloridaStructures.shp",
        "csv_name": "SS.csv",
    },
}

class FMSFImporter(BaseImportModule):
    def __init__(self, request=None):

        if request:
            loadid = request.POST.get("load_id")

        self.request = request if request else None
        self.userid = request.user.id if request else None
        self.loadid = None
        self.moduleid = request.POST.get("module") if request else None
        self.datatype_factory = DataTypeFactory()

        # ETLResult object that will be assigned at the beginning of run_sequence()
        self.reporter = None

        # these are passed into the two different import process methods
        self.file_dir = None
        self.resource_type = None

        # these are set in the _set_resource_type() method
        self.graph = None
        self.field_map = {}
        self.resource_csv = None
        self.resource_shp = None
        self.extra_structures_csv = None

        # holding and managing feature content during the import process
        self.features = []
        self.new_features = []
        self.existing_features = []
        self.tiles = []
        self.fmsf_resources = []
        self.extra_structures = []

        self.blank_tile_lookup = {}
        self.concept_lookups = {}
        self.node_lookup = {}
        self.nodegroup_lookup = {}
        self.resource_lookup = {}
        self.special_label_lookups = specials

    def get_uploaded_files_location(self):
        self.file_dir = Path(settings.APP_ROOT, "fmsf-uploads", self.loadid)
        return Path(settings.APP_ROOT, "fmsf-uploads", self.loadid)

    def _set_resource_type(self, resource_type):
        self.resource_type = resource_type
        self.resource_shp = Path(self.file_dir, FILENAME_LOOKUP[resource_type]["shp_name"])
        self.resource_csv = Path(self.file_dir, FILENAME_LOOKUP[resource_type]["csv_name"])
        self.graph = GraphModel.objects.get(name=resource_type)
        self.field_map = field_maps[resource_type]

    def _set_resource_lookup(self):
        resources = Resource.objects.filter(graph=self.graph)
        for resource in resources:
            try:
                siteid = resource.get_node_values("FMSF ID")[0]
            except IndexError:
                logger.warn(f"orphan resource: {resource.pk} has no FMSF ID")
                continue
            self.resource_lookup[siteid] = resource

    def delete_from_default_storage(self, directory):
        dirs, files = default_storage.listdir(directory)
        for dir in dirs:
            dir_path = os.path.join(directory, dir)
            self.delete_from_default_storage(dir_path)
        for file in files:
            file_path = os.path.join(directory, file)
            default_storage.delete(file_path)
        default_storage.delete(directory)

    def read_zip(self, request):
        """
        Reads added zip package of shapefile and CSV file. This is the entry point
        for the front-end generated workflow, and the loadid is generated here.
        """

        if self.loadid is None:
            self.loadid = str(uuid.uuid4())

        response = {
            'operation': 'read_zip',
            'success': True,
            'message': "",
            'data': {
                'Files': [],
                'loadid': self.loadid,
            }
        }

        content = request.FILES.get("file")
        upload_dir = self.get_uploaded_files_location()
        try:
            self.delete_from_default_storage(upload_dir)
        except (FileNotFoundError):
            pass

        zip_types = [
            "application/zip",
            "application/x-zip-compressed",
        ]

        try:
            if content.content_type in zip_types:
                with zipfile.ZipFile(content, "r") as zip_ref:
                    files = zip_ref.infolist()
                    for file in files:
                        response['data']['Files'].append(file.filename)
                        save_path = Path(upload_dir, Path(file.filename).name)
                        default_storage.save(save_path, File(zip_ref.open(file)))
            else:
                logger.warn(f"uploaded content_type is not zip, is {content.content_type}")
                response['success'] = False
                response['message'] = "Uploaded file must be a .zip file."
                return response
        except Exception as e:
            logger.error(e)
            response['success'] = False
            response['message'] = str(e)
            return response

        return response

    def _read_resource_csv(self):

        # read the CSV into a list of rows, trying different encodings
        try:
            # First try to read as UTF encoded file
            with open(self.resource_csv, "r", encoding="utf-8") as in_csv:
                reader = csv.DictReader(in_csv)
                rows = [i for i in reader]
        except UnicodeDecodeError:
            # If that doesn't work, try ISO-8859-1 (common in windows)
            with open(self.resource_csv, "r", encoding="ISO-8859-1") as in_csv:
                reader = csv.DictReader(in_csv)
                rows = [i for i in reader]
        except Exception as e:
            logger.error(e)
            raise e

        data = {}
        for row in rows:
            siteid = row['SiteID'].rstrip()
            data[siteid] = data.get(siteid, []) + [row]

        self.csv_data = data

    def get_value_from_csv(self, siteid, field_name):
        """ the trick here is that the CSV data will have multiple rows per
        siteid (site forms submitted over the years). For now, just iterate these
        rows and return the last row that has a non-empty value for this field. """
        value = None
        if siteid in self.csv_data:
            for i in self.csv_data[siteid]:
                form_value = i.get(field_name, "")
                if form_value.rstrip() != "":
                    value = form_value
        return value


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

    def validate_files(self, file_dir):

        def validate_shp_fields(layer):
            shp_fields = []
            for fieldset in self.field_map.values():
                for item in fieldset:
                    if item['source'] == "shp" and not item['field'] == "geom":
                        shp_fields.append(item['field'])
            return [i for i in shp_fields if not i in layer.fields]

        if isinstance(file_dir, str):
            file_dir = Path(file_dir)

        # first make sure the SHP and CSV are present
        for path in [self.resource_shp, self.resource_csv]:
            if not path.is_file():
                self.reporter.success = False
                self.reporter.message = f"Expected file {self.resource_shp.name} is missing."

        # next check the shapefile and its fields
        if self.reporter.success:
            try:
                ds = DataSource(self.resource_shp)
                lyr = ds[0]
                self.reporter.message = "All files look good!"
                missing = validate_shp_fields(lyr)
                if len(missing) > 0:
                    self.reporter.success = False
                    self.reporter.message = f"Shapefile is missing these fields: {', '.join(missing)}"
                    self.reporter.data['Missing Fields'] = missing
            except Exception as e:
                self.reporter.success = False
                self.reporter.message = str(e)

        # finally, check the extra-structures CSV if it is present
        if self.reporter.success:
            extra_structures_csv = Path(file_dir, "extra-structures.csv")
            if extra_structures_csv.is_file():
                with open(extra_structures_csv, "r") as o:
                    reader = csv.reader(o)
                    headers = next(reader)
                    if headers[0] != "SiteID":
                        self.reporter.success = False
                        self.reporter.message = f"extra-structures.csv missing required header: SiteID"

        self.reporter.log(logger)
        return

    def initialize_load_event(self, load_description=""):

        if self.moduleid is None:
            self.moduleid = ETLModule.objects.get(classname=self.__class__.__name__).pk
        if self.userid is None:
            self.userid = 1

        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO load_event (loadid, complete, status, load_description, etl_module_id, load_details, load_start_time, user_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (self.loadid, False, "running", load_description, self.moduleid, self.reporter.get_load_details(), datetime.now(), self.userid),
            )

        self.reporter.message = f"etl started with loadid: {self.loadid}"
        return

    def apply_historical_structures_filter(self, only_extra_ids=False):

        self.update_status_and_load_details("filtering")

        def _feature_is_lighthouse(feature):
            vals = [feature.get(f"STRUCUSE{i}") for i in [1,2,3]]
            return any([i for i in vals if i and i.lower() == "lighthouse"])

        def _feature_is_destroyed(feature):
            return feature.get("DESTROYED") == "YES"

        extra_ids = []
        extra_structures_csv = Path(self.file_dir, "extra-structure-ids.csv")
        if extra_structures_csv.is_file():
            with open(extra_structures_csv, "r") as openf:
                reader = csv.reader(openf)
                next(reader)
                for row in reader:
                    extra_ids.append(row[0])
        logger.debug(f"extra ids to import: {len(extra_ids)}")

        extra_list, lighthouse_list, geom_list = [], [], []
        for feature in self.new_features:
            siteid = feature.get("SITEID").rstrip()
            # include any special ids
            if siteid in extra_ids:
                extra_list.append(siteid)
                continue
            # if only_extra_ids, skip all the rest of the resources
            if only_extra_ids is True:
                continue

            # skip structure marked as destroyed
            if _feature_is_destroyed(feature):
                continue
            # now, collect sites that are (or were) lighthouses
            if _feature_is_lighthouse(feature):
                lighthouse_list.append(siteid)
            # for all others, collect geometry to filter by location
            else:
                geom_list.append((siteid, feature.geom.wkt))

        # CREATE AND RUN GEOMETRY FILTER AGAINST SELECTED MANAGEMENT AREAS
        geom_matches = []
        union_geom = None
        if len(geom_list) > 0:
            logger.debug("unioning Management Areas")
            filter_areas = ManagementArea.objects.exclude(category__name__in=["FPAN Region", "County"])
            # filter_areas = ManagementArea.objects.filter(pk=352)
            try:
                union_results = filter_areas.aggregate(Union('geom'))
            except Exception as e:
                self.reporter.success = False
                self.reporter.message = str(e)
                return

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

        use_list = set(lighthouse_list + geom_matches + extra_list)

        original_ct = len(self.new_features)

        self.new_features = [i for i in self.new_features if i.get("SITEID") in use_list]
        final_features = [i for i in self.new_features if i.get("SITEID") in use_list]
        del self.new_features
        del union_geom
        gc.collect()

        self.new_features = final_features

        self.reporter.message = f"{len(self.new_features)} out of {original_ct} left after structure filter"
        self.reporter.data['Filtered structures'] = len(self.new_features)
        return

    def read_features_from_shapefile(self):

        ds = DataSource(self.resource_shp)
        lyr = ds[0]

        for feature in lyr:
            self.features.append(feature)
            siteid = feature.get("SITEID").rstrip()
            if siteid in self.resource_lookup:
                self.existing_features.append(feature)
            else:
                self.new_features.append(feature)

        self.reporter.data['Sites already in database'] = len(self.existing_features)
        self.reporter.data['New sites in uploaded data'] = len(self.new_features)
        self.reporter.message = f"features: new - {len(self.new_features)}, existing {len(self.existing_features)}"

        self.reporter.log(logger)
        return

    def generate_load_data(self, truncate=None):

        self.update_status_and_load_details("generating")

        logger.debug("reading csv")
        self._read_resource_csv()

        self.tiles = []
        self.fmsf_resources = []

        logger.debug("generating load data")
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

        self.reporter.message = f"resources: {len(self.fmsf_resources)}, tiles: {len(self.tiles)}"
        self.reporter.data["Features to load"] = len(self.fmsf_resources)
        self.reporter.data["Tiles to load"] = len(self.tiles)
        self.reporter.data["New FMSF site ids"] = [i.siteid for i in self.fmsf_resources]

        # This summary file of ids was a nice idea, but it is failing because
        # of file permissions: apache creates the directory, and then celery
        # tries to write this file to it and doesn't have permission.
        # Disabling this for the time being...
#        try:
#            csv_summary_file = Path(self.file_dir, "sites_loaded.csv")
#            with open(csv_summary_file, "w") as f:
#                writer = csv.writer(f)
#                writer.writerow(("SITEID", "ResourceId"))
#                writer.writerows([(i.siteid, i.resourceid) for i in self.fmsf_resources])
#        except Exception as e:
#            logger.info("error trying to write csv, probably a dumb error")
#            logger.info(e)

        self.reporter.log(logger)
        return

    def write_data_to_load_staging(self):

        self.update_status_and_load_details("staging")

        logger.debug("writing data to load_staging table")
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
            self.reporter.message = f"{len(self.tiles)} tiles written to load_staging table"
        except Exception as e:
            self.reporter.success = False
            self.reporter.message = str(e)

        self.reporter.log(logger)
        return

    def write_tiles_from_load_staging(self):

        self.update_status_and_load_details("writing")

        logger.debug("writing tiles from load_staging")
        try:
            with connection.cursor() as cursor:
                # cursor.execute("""CALL __arches_prepare_bulk_load();""")
                cursor.execute("""ALTER TABLE tiles disable trigger __arches_check_excess_tiles_trigger;""")
                cursor.execute("""ALTER TABLE tiles disable trigger __arches_trg_update_spatial_attributes;""")
            with connection.cursor() as cursor:
                cursor.execute("""SELECT * FROM __arches_staging_to_tile(%s)""", [self.loadid])
                row = cursor.fetchall()
            self.reporter.message = f"all tiles written to tile table"
            if row[0][0]:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """UPDATE load_event SET (status, load_end_time, load_details) = (%s, %s, %s) WHERE loadid = %s""",
                        ("loaded", datetime.now(), self.reporter.get_load_details(), self.loadid),
                    )
            else:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """UPDATE load_event SET (status, load_end_time) = (%s, %s) WHERE loadid = %s""",
                        ("failed", datetime.now(), self.loadid),
                    )
                self.reporter.success = False
                self.reporter.message = "No rows resulted from the write process"
        except (IntegrityError, ProgrammingError) as e:
            with connection.cursor() as cursor:
                cursor.execute(
                    """UPDATE load_event SET (status, load_end_time) = (%s, %s) WHERE loadid = %s""",
                    ("failed", datetime.now(), self.loadid),
                )
            self.reporter.success = False
            self.reporter.message = str(e)
        finally:
            with connection.cursor() as cursor:
                # cursor.execute("""CALL __arches_complete_bulk_load();""")
                cursor.execute("""ALTER TABLE tiles enable trigger __arches_check_excess_tiles_trigger;""")
                cursor.execute("""ALTER TABLE tiles enable trigger __arches_trg_update_spatial_attributes;""")

        self.reporter.log(logger)
        return

    def finalize_indexing(self):

        try:
            self.update_status_and_load_details("indexing")
            index_resources_by_transaction(self.loadid, quiet=True, use_multiprocessing=False)
            with connection.cursor() as cursor:
                cursor.execute(f"REFRESH MATERIALIZED VIEW mv_geojson_geoms;")
            with connection.cursor() as cursor:
                cursor.execute(
                    """UPDATE load_event SET (status, indexed_time, complete, successful, load_details) = (%s, %s, %s, %s, %s) WHERE loadid = %s""",
                    ("completed", datetime.now(), True, True, self.reporter.get_load_details(), self.loadid),
                )
            self.reporter.message = "resources indexed and materialized view refreshed"
        except Exception as e:
            self.reporter.success = False
            self.reporter.message = str(e)

        self.reporter.log(logger)
        return

    def run_web_import(self, request):

        # handle values coming from frontend configuration
        resource_type = request.POST.get('resourceType')
        truncate = request.POST.get('truncate')
        dry_run = request.POST.get('dryRun')
        description = request.POST.get('loadDescription')
        only_extra_ids = request.POST.get('onlySiteIdList')
        loadid = request.POST.get('loadId')
        self.resource_type = resource_type
        if truncate == "0":
            truncate = None
        if dry_run == "true":
            dry_run = True
        else:
            dry_run = False
        if only_extra_ids == "true":
            only_extra_ids = True
        else:
            only_extra_ids = False

        run_sequence_as_task.delay(loadid, resource_type, truncate=truncate, dry_run=dry_run, description=description, only_extra_ids=only_extra_ids)

        return {
            "message": "import task submitted",
            "loadId": loadid,
            "success": True,
            "data": {},
        }

    def run_cli_import(self, **kwargs):

        resource_type = kwargs.get("resource_type", None)
        dry_run = kwargs.get("dry_run", False)
        truncate = kwargs.get("truncate")

        if resource_type is None:
            raise Exception("resource_type must be provided")
        if truncate is not None:
            truncate = int(truncate)
        file_dir = kwargs.get("file_dir")
        if file_dir is None:
            raise Exception("file_dir must be provided")

        self.run_sequence(resource_type, truncate=truncate, dry_run=dry_run, file_dir=file_dir)

        return self.reporter.serialize()

    def run_sequence(self, resource_type, loadid=None, truncate=None, dry_run=False, file_dir=None, description="", only_extra_ids=False):

        # the loadid may or may not be created already, but now it must be
        # and added to this instance for use in all the subsequent operations.
        if loadid is None:
            loadid = str(uuid.uuid4())
        self.loadid = loadid

        if truncate is None:
            truncate_str = "false"
        if truncate is not None:
            truncate = int(truncate)
            truncate_str = str(truncate)

        if file_dir is None:
            file_dir = self.get_uploaded_files_location()
        else:
            self.file_dir = file_dir

        self.reporter = ETLOperationResult(
            inspect.currentframe().f_code.co_name,
            loadid=self.loadid,
            data={
                "Dry run": dry_run,
                "Truncate load": truncate_str,
                "Resource model": resource_type,
            }
        )

        if only_extra_ids is True:
            self.reporter.data['Only use extra ids'] = True

        # use the provided resource_type to reference the proper graph and import files
        self._set_resource_type(resource_type)

        # START THE PROCESS
        self.initialize_load_event(load_description=description)

        # RUN FILE VALIDATION
        self.validate_files(file_dir)
        if self.reporter.success is False:
            return self.abort_load()

        # create lookup of all existing resource instances for comparison
        self._set_resource_lookup()

        # READ FEATURES FROM THE INPUT SHAPEFILE
        self.read_features_from_shapefile()
        if len(self.new_features) == 0:
            return self.abort_load(status="completed")

        # RUN FILTERS ON THE STRUCTURES, IF NECESSARY
        if self.resource_type == "Historic Structure":
            self.apply_historical_structures_filter(only_extra_ids=only_extra_ids)
            if self.reporter.success is False:
                return self.abort_load()

        # GENERATE THE DATA TO BE LOADED
        self.generate_load_data(truncate=truncate)
        if self.reporter.success is False:
            return self.abort_load()

        # WRITE THE LOAD DATA TO THE STAGING TABLE IN ARCHES DB
        self.write_data_to_load_staging()
        if self.reporter.success is False:
            return self.abort_load()

        # RUN THE FUNCTION TO TRANSLATE THE STAGING TABLE INTO REAL TILES
        if dry_run is True:
            self.reporter.message = f"Dry run completed successfully with {len(self.fmsf_resources)} resources."
            self.finalize_indexing()
        else:
            self.write_tiles_from_load_staging()
            if self.reporter.success is False:
                return self.abort_load()

            # write the cumulative reporter data to load_details in the final step
            self.finalize_indexing()
            if self.reporter.success is False:
                return self.abort_load()

            self.reporter.message = "completed without error"

        return self.reporter.serialize()

    def update_status_and_load_details(self, status):
        """
        Sets the load_event status as specified and updates the load_details
        object from the current state of self.reporter
        """

        with connection.cursor() as cursor:
            cursor.execute(
                """UPDATE load_event SET (status, load_details) = (%s, %s) WHERE loadid = %s""",
                (status, self.reporter.get_load_details(), self.loadid),
            )

    def abort_load(self, status="failed"):
        """
        Writes a failure/abort message to the load_event table, based on the current content
        of the self.reporter object. Status can be overridden for cases where the abort
        is not due to error, but just a lack of new data to load.
        """

        with connection.cursor() as cursor:
            cursor.execute(
                """UPDATE load_event SET (status, error_message, load_details, complete, successful) = (%s, %s, %s, %s, %s) WHERE loadid = %s""",
                (status, self.reporter.message, self.reporter.get_load_details(), True, True, self.loadid),
            )

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
                if ma.management_agency is not None:
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
                        cursor.execute(f"SELECT ST_AsGeoJSON( ST_RemoveRepeatedPoints( ST_MakeValid('{geom.wkt}')));")
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
                        importer.resource_csv.name,
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
                importer.resource_csv.name,
                passes_validation,
            )
            tiles.append(row)

        return tiles
