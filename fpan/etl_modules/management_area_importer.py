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

from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from django.contrib.gis.gdal import DataSource, SpatialReference
from django.contrib.gis.db.models import Union
from django.db import connection, transaction
from django.db.models import Q
from django.db.utils import IntegrityError, ProgrammingError
from django.utils.translation import ugettext as _
from django.core.files import File
from django.core.files.storage import default_storage
from django.conf import settings

from arches.app.datatypes.datatypes import DataTypeFactory
from arches.app.etl_modules.base_import_module import BaseImportModule
from arches.app.models.concept import Concept
from arches.app.models.models import GraphModel, Node, NodeGroup, ETLModule, ResourceInstance
from arches.app.models.tile import Tile
from arches.app.models.resource import Resource
from arches.app.utils.betterJSONSerializer import JSONSerializer
from arches.app.utils.index_database import index_resources_by_transaction

from hms.models import (
    ManagementArea,
    ManagementAreaGroup,
    ManagementAreaCategory,
    ManagementAgency,
)
from fpan.tasks import run_management_area_import_as_task
from fpan.utils import ETLOperationResult, SpatialJoin

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

        # these are set at the beginning of run_sequence
        self.group = None
        self.category = None
        self.agency = None
        self.level = None

        # holding and managing new content during the import process
        self.areas = []

        self.blank_tile_lookup = {}
        self.node_lookups = {}
        self.nodegroup_lookup = {}
        self.resource_lookup = {}

    def _get_node_lookup(self, graph_name):

        if not graph_name in self.node_lookups:
            self.node_lookups[graph_name] = {
                "FPAN Region": str(Node.objects.get(graph__name=graph_name, name="FPAN Region").pk),
                "County": str(Node.objects.get(graph__name=graph_name, name="County").pk),
                "Management Area": str(Node.objects.get(graph__name=graph_name, name="Management Area").pk),
                "Management Agency": str(Node.objects.get(graph__name=graph_name, name="Management Agency").pk),
            }
        return self.node_lookups[graph_name]

    def _get_nodegroup(self, graph_name):

        if not graph_name in self.nodegroup_lookup:
            self.nodegroup_lookup[graph_name] = str(Node.objects.get(graph__name=graph_name, name="Site Management").nodegroup.pk)
        return self.nodegroup_lookup[graph_name]

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
        Reads added zipped shapefile. This is the entry point
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

    def validate_files(self, file_dir):

        if isinstance(file_dir, str):
            file_dir = Path(file_dir)

        shp_file = [i for i in file_dir.glob("*.shp")][0]
        self.file_path = shp_file
        self.reporter.data['File name'] = self.file_path.name

        try:
            ds = DataSource(self.file_path)
            lyr = ds[0]
            self.reporter.message = "All files look good!"
            name_field_present = "name" in [i.lower() for i in lyr.fields]
            if not name_field_present:
                self.reporter.success = False
                self.reporter.message = "Shapefile is missing 'name' field"
            if lyr.srs.srid != 4326:
                self.reporter.success = False
                self.reporter.message = "Shapefile must be reprojected to WGS84 / EPSG:4326"
        except Exception as e:
            self.reporter.success = False
            self.reporter.message = str(e)

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

        self.update_status_and_load_details("creating areas")
        ds = DataSource(self.file_path)
        lyr = ds[0]
        name_field = [i for i in lyr.fields if i.lower() == "name"][0]
        logger.debug("name field: " + name_field)
        try:
            with transaction.atomic():
                for feature in lyr:
                    logger.debug(feature)
                    geom = GEOSGeometry(feature.geom.wkt)
                    if geom.geom_type == "Polygon":
                        geom = MultiPolygon([geom])
                    with connection.cursor() as cursor:
                        cursor.execute(f"SELECT ST_AsGeoJSON( ST_RemoveRepeatedPoints( ST_MakeValid('{geom.wkt}')));")
                        wkt = cursor.fetchone()[0]
                    logger.debug("geom handled")
                    name = feature.get(name_field)
                    logger.debug("name: " + name)
                    ma = ManagementArea.objects.create(
                        geom=wkt,
                        name=feature.get(name_field),
                        category=self.category,
                        management_agency=self.agency,
                        management_level=self.level,
                        load_id=self.loadid,
                    )
                    logger.debug("obj created")
                    if self.group:
                        self.group.areas.add(ma)
                    ma.save()
                    self.areas.append(ma)

        except Exception as e:
            self.reporter.success = False
            self.reporter.message = str(e)

        self.reporter.log(logger)
        return

    def apply_spatial_join(self):

        self.update_status_and_load_details("running spatial join")

        joiner = SpatialJoin()
        for area in self.areas:
            self.update_status_and_load_details(f"processing {area.name}")
            joiner.join_management_area_to_resources(area)

    def finalize_load(self):

        try:
            self.update_status_and_load_details("finalizing load")
            with connection.cursor() as cursor:
                cursor.execute(
                    """UPDATE load_event SET (status, indexed_time, complete, successful, load_details) = (%s, %s, %s, %s, %s) WHERE loadid = %s""",
                    ("completed", datetime.now(), True, True, self.reporter.get_load_details(), self.loadid),
                )
            self.reporter.message = "management area import complete"
        except Exception as e:
            self.reporter.success = False
            self.reporter.message = str(e)

        self.reporter.log(logger)
        return

    def run_web_import(self, request):

        # handle values coming from frontend configuration
        ma_group = request.POST.get('maGroup')
        ma_category = request.POST.get('maCategory')
        ma_agency = request.POST.get('maAgency')
        ma_level = request.POST.get('maLevel')
        description = request.POST.get('loadDescription')
        loadid = request.POST.get('loadId')

        ma_group = None if ma_group == "---" else ma_group
        ma_category = None if ma_category == "---" else ma_category
        ma_agency = None if ma_agency == "---" else ma_agency
        ma_level = None if ma_level == "---" else ma_level

        run_management_area_import_as_task.delay(
            loadid,
            ma_group=ma_group,
            ma_category=ma_category,
            ma_agency=ma_agency,
            ma_level=ma_level,
            description=description,
        )

        return {
            "message": "import task submitted",
            "loadId": loadid,
            "success": True,
            "data": {},
        }

    def run_cli_import(self, **kwargs):

        self.run_sequence(
            file_dir=kwargs.get("file_dir"),
            ma_group=kwargs.get("ma_group"),
            ma_category=kwargs.get("ma_category"),
            ma_agency=kwargs.get("ma_agency"),
            ma_level=kwargs.get("ma_level"),
            description=kwargs.get("description", ""),
        )

        return self.reporter.serialize()

    def reverse_load(self, **kwargs):

        loadid = kwargs.get("loadid")
        if loadid is None:
            logger.error("loadid must be provided. Cancelling load reversal.")
            raise(Exception("No loadid provided"))

        objs = ManagementArea.objects.filter(load_id=loadid)
        logger.info(f"removing {objs.count()} Management Areas matching loadid {loadid}")
        objs.delete()
        with connection.cursor() as cursor:
            cursor.execute(
                """DELETE FROM load_event WHERE loadid = %s""", (loadid,),
            )
        return

    def run_sequence(self, loadid=None, file_dir=None, ma_group=None, ma_category=None, ma_agency=None, ma_level=None, description=""):

        logger.debug("begin run_sequence...")
        # the loadid may or may not be created already, but now it must be
        # and added to this instance for use in all the subsequent operations.
        if loadid is None:
            loadid = str(uuid.uuid4())
        self.loadid = loadid

        # file_dir should be passed in through the cli invokation, but not web
        if file_dir is None:
            file_dir = self.get_uploaded_files_location()
        else:
            self.file_dir = file_dir

        # handle the objects here
        if ma_group is not None:
            self.group = ManagementAreaGroup.objects.get(pk=int(ma_group))
        if ma_category is not None:
            self.category = ManagementAreaCategory.objects.get(pk=int(ma_category))
        if ma_agency is not None:
            self.agency = ManagementAgency.objects.get(pk=ma_agency)
        self.level = ma_level

        self.reporter = ETLOperationResult(
            inspect.currentframe().f_code.co_name,
            loadid=self.loadid,
            data={
                "Load ID": self.loadid,
                "Management Area Group": self.group.name if self.group else "---",
                "Management Area Category": self.category.name if self.category else "---",
                "Management Agency": self.agency.name if self.agency else "---",
                "Management Area Level": self.level,
            }
        )

        # START THE PROCESS
        logger.debug("initialize load event...")
        self.initialize_load_event(load_description=description)

        # RUN FILE VALIDATION
        logger.debug("validate files...")
        self.validate_files(file_dir)
        if self.reporter.success is False:
            return self.abort_load()

        # READ FEATURES FROM THE INPUT SHAPEFILE
        logger.debug("read input shapefile...")
        self.read_features_from_shapefile()
        if self.reporter.success is False:
            return self.abort_load()

        # APPLY THE SPATIAL JOIN WITH ALL INTERSECTING FEATURES
        logger.debug("apply spatial join...")
        self.apply_spatial_join()
        if self.reporter.success is False:
            return self.abort_load()

        self.finalize_load()

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
