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
    "etlmoduleid": "3aaaa76a-0b09-450e-bee1-bbaccb0960bb",
    "name": "Management Area Importer",
    "description": "Loads management area objects from a shapefile",
    "etl_type": "import",
    "component": "views/components/etl_modules/management-area-importer",
    "componentname": "management-area-importer",
    "modulename": "management_area_importer.py",
    "classname": "ManagementAreaImporter",
    "config": {"circleColor": "rgb(80, 176, 198)", "bgColor": "rgb(68, 136, 157)", "show": True},
    "icon": "fa fa-upload",
    "slug": "management-area-importer"
}


class ManagementAreaImporter(BaseImportModule):
    def __init__(self, request=None):

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

    def get_uploaded_files_location(self):
        self.file_dir = Path(settings.APP_ROOT, "management-area-uploads", self.loadid)
        return self.file_dir

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
        upload_dir = str(self.get_uploaded_files_location())

        try:
            self.delete_from_default_storage(upload_dir)
        except (FileNotFoundError):
            pass
        except Exception as e:
            logger.error(e)

        zip_types = [
            "application/zip",
            "application/x-zip-compressed",
        ]

        try:
            if content.content_type in zip_types:
                with zipfile.ZipFile(content, "r") as zip_ref:
                    files = zip_ref.infolist()
                    zip_ref.extractall(upload_dir)
                    for file in files:
                        response['data']['Files'].append(file.filename)
                        # save_path = Path(upload_dir, Path(file.filename).name)
                        # default_storage.save(save_path, File(zip_ref.open(file)))
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

    def read_features_from_shapefile(self):

        ds = DataSource(self.resource_shp)
        lyr = ds[0]

        for feature in lyr:
            self.features.append(feature)
            print(feature)

        self.reporter.data['Areas to upload'] = len(self.feature)
        self.reporter.message = f"Areas: new - {len(self.feature)}"

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
                "Load ID": self.loadid,
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
