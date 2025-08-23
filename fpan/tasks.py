from __future__ import absolute_import, unicode_literals
import logging
from celery import shared_task

from arches.app.models.resource import Resource

logger = logging.getLogger(__name__)

@shared_task
def run_sequence_as_task(loadid, resource_type, truncate=None, dry_run=False, description="", only_extra_ids=False):
    from fpan.etl_modules.fmsf_importer import FMSFImporter
    FMSFImporter().run_sequence(
        resource_type,
        loadid=loadid,
        truncate=truncate,
        dry_run=dry_run,
        description=description,
        only_extra_ids=only_extra_ids,
    )

@shared_task
def run_management_area_import_as_task(loadid, ma_group=None, ma_category=None, ma_agency=None, ma_level=None, description=""):
    from fpan.etl_modules.management_area_importer import ManagementAreaImporter
    ManagementAreaImporter().run_sequence(
        loadid=loadid,
        ma_group=ma_group,
        ma_category=ma_category,
        ma_agency=ma_agency,
        ma_level=ma_level,
        description=description,
    )

@shared_task
def run_full_spatial_join():
    from arches.app.models.models import ResourceInstance
    from fpan.utils import SpatialJoin
    joiner = SpatialJoin()

    resource_graphs = ["Archaeological Site", "Historic Cemetery", "Historic Structure"]
    for res in ResourceInstance.objects.filter(graph__name__in=resource_graphs):
        logger.debug(f"spatial join resource: {res.pk}")
        joiner.update_resource(res)


################################################################################
# Download Report Photos

# TODO: move constants to fpan settings
# TODO: where will we store zip downloads?
# TODO: are we always looking in S3 for uploads? assume yes -- but how often is the S3 dump happening?
# TODO: swap local source dir for S3 bucket && update file zipping logic
# TODO: clean up the cache periodically
# TODO: logging

from pathlib import Path
from zipfile import ZipFile
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

REPORT_PHOTOS_SOURCE_DIR = "fpan/uploadedfiles"
REPORT_PHOTOS_ZIP_DIR = "fpan/report_photo_downloads"

@shared_task
def zip_photos_for_download(reportid) -> str:
    """
    Gather photos related to `reportid`, zip them, and return the filename of
    the zip file.
    """
    zip_filename = f"{reportid}.zip"
    zippath = Path(f"{REPORT_PHOTOS_ZIP_DIR}/{zip_filename}")


    # TODO: will caching cause issues? is it worth the trade off to not cache?
    if zippath.exists():
        return zip_filename

    # add parent dirs of dest dir if needed (like bash mkdir)
    zippath.parent.mkdir(parents=True, exist_ok=True)

    photo_filenames = photos_list(reportid)

    with ZipFile(zippath, "w") as zip_file:
        for filename in photo_filenames:
            # TODO: error handling - how could this fail?
            # - file does not exist somehow
            photo_path = Path(f"{REPORT_PHOTOS_SOURCE_DIR}/{filename}")
            zip_file.write(photo_path, arcname=filename)

    return zip_filename


################################################################################
# HELPERS FOR zip_photos_for_download

from arches.app.models.models import Node
from arches.app.models.tile import Tile


# TODO: FIX ME: i am a hastily hacked version of a method from make_file_list method
# TODO: TEST ME
#     - does this return only photo filenames?
#     - does this gather MORE than the given report's associated filenames?
#         or does it recurse thru all related notes, gathering associate filenames?
def photos_list(resourceid: str) -> list[str]:
    # TODO: make this not a list -- only need one
    resources = []
    id = resourceid

    ## collect resources from arguments
    r = Resource.objects.get(pk=id)
    resources.append(r)

    ## make list of individual resource entries
    output = []
    for res in resources:
        entry = processed_resource(res)
        output.append(entry)

    ## make list of names for file nodes
    node_columns = set()
    for res in output:
        for node_name in res["file_data"].keys():
            node_columns.add(node_name)
    
    ## iterate all resource entries and create a row (list) for each one
    rows = []
    for res in output:
        row = [res["resourceid"], res["name"]]
        for file_node in node_columns:
            row.append(res["file_data"].get(file_node))
        rows.append(row)

    # output = [
    #     ["resourceid", "name"] + list(node_columns)
    # ]
    output = []
    for row in rows:
        output.append(row)

    PHOTO_FILENAME_INDEX = 2

    output = list(map(lambda item: item[PHOTO_FILENAME_INDEX], output))[0]

    print()
    print("OUTPUT OF PHOTOS LIST")
    print(output)
    print()

    return output


# TODO: FIX ME: i am a hastily hacked version of a method from make_file_list method
# TODO: TEST ME
def processed_resource(resource):
    ## get all file-list nodes for this resource's graph
    nodes = Node.objects.filter(datatype="file-list", graph__name=resource.graph.name)

    ## create lookup of node id to node name (to use later)
    node_lookup = {str(i.pk):i.name for i in nodes}

    ## stub out entry for this resource
    output = {
        "name": resource.displayname(),
        "resourceid": str(resource.pk),
        "file_data": {}
    }

    ## stub out file data dict with all possible nodes for this resource
    stage_data = {str(i.pk): [] for i in nodes}

    ## get all tiles for this resource that contain any relevant nodes
    nodegroups = [i.nodegroup for i in nodes]
    tiles = Tile.objects.filter(nodegroup__in=nodegroups, resourceinstance=resource)

    ## iterate tiles and collect node data into
    for tile in tiles:
        for k, v in tile.data.items():
            if k in node_lookup:
                # lose a little fidelity here by collapsing multiple instances of nodes but oh well
                if v:
                    stage_data[k] += v

    ## use staged data and node_lookup to transform UUIDs to readable strings
    for k, v in stage_data.items():
        if len(v) > 0:
            output["file_data"][node_lookup[k]] = [i["name"] for i in v]

    return output
