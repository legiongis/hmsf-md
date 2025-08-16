import logging
from django.core.cache import cache
from django.http import FileResponse, Http404, HttpRequest, HttpResponse, HttpResponseBadRequest
from django.db import connection
from django.db.utils import IntegrityError
from arches.app.models import models
from arches.app.views.api import APIBase
from arches.app.models.system_settings import settings
from arches.app.models.resource import Resource
from arches.app.models.graph import Graph
from arches.app.utils.response import JSONResponse

from fpan.search.components.rule_filter import RuleFilter

logger = logging.getLogger(__name__)

class MVT(APIBase):
    EARTHCIRCUM = 40075016.6856
    PIXELSPERTILE = 256
    EMPTY_TILE = HttpResponse(b'', content_type="application/x-protobuf")

    def get(self, request, nodeid, zoom, x, y):
        if hasattr(request.user, "userprofile") is not True:
            try:
                models.UserProfile.objects.create(user=request.user)
            except IntegrityError as e:
                logger.warning(e)
                raise Http404()
        viewable_nodegroups = request.user.userprofile.viewable_nodegroups
        try:
            node = models.Node.objects.get(nodeid=nodeid, nodegroup_id__in=viewable_nodegroups)
        except models.Node.DoesNotExist:
            raise Http404()
        config = node.config
        cache_key = f"mvt_{nodeid}_{request.user.username}_{zoom}_{x}_{y}"
        tile = cache.get(cache_key)

        BUST_RESOURCE_LAYER_CACHE = True
        if tile is None or BUST_RESOURCE_LAYER_CACHE is True:

            ## disable the real postgis spatial query because it was slower (and more picky about the input geometry)
            ## than just calling another geo query on ES and retrieving ids from
            ## that. could use another look down the road...
            # rules = SiteFilter().get_rules(request.user, str(node.graph_id))
            # if rule.type == "geo_filter":
            #     geom = rules["geometry"]
            #     # ST_SetSRID({geom}, 4236)
            #     resid_where = f"ST_Intersects(geom, ST_Transform('{geom}', 3857))"

            query_params = {
                'nodeid': nodeid,
                'zoom': zoom,
                'x': x,
                'y': y,
            }

            graphid = str(node.graph_id)
            rule = RuleFilter().compile_rules(request.user, graphids=[graphid], single=True)
            full_access = False
            if rule.type == "no_access":
                return self.EMPTY_TILE
            elif rule.type == "full_access":
                full_access = True
            else:
                resids = RuleFilter().get_resources_from_rule(rule, ids_only=True)
                # if there are not sites this user can view, return and empty tile before
                # creating a db connection
                if len(resids) == 0:
                    return self.EMPTY_TILE
                # otherwise, add the list of valid ids to query params to be used below
                query_params['valid_resids'] = tuple(resids)

            with connection.cursor() as cursor:

                if int(zoom) <= int(config["clusterMaxZoom"]):
                    arc = self.EARTHCIRCUM / ((1 << int(zoom)) * self.PIXELSPERTILE)
                    # add some extra query_params to support clustering
                    query_params['distance'] = arc * int(config["clusterDistance"])
                    query_params['min_points'] = int(config["clusterMinPoints"])

                    if full_access:
                        # run the basic cluster request and return ALL resources
                        cursor.execute(
                            """WITH clusters(tileid, resourceinstanceid, nodeid, geom, cid)
                            AS (
                                SELECT m.*,
                                ST_ClusterDBSCAN(geom, eps := %(distance)s, minpoints := %(min_points)s) over () AS cid
                                FROM (
                                    SELECT tileid,
                                        resourceinstanceid,
                                        nodeid,
                                        geom
                                    FROM geojson_geometries
                                    WHERE nodeid = %(nodeid)s
                                ) m
                            )

                            SELECT ST_AsMVT(
                                tile,
                                %(nodeid)s,
                                4096,
                                'geom',
                                'id'
                            ) FROM (
                                SELECT resourceinstanceid::text,
                                    row_number() over () as id,
                                    1 as total,
                                    ST_AsMVTGeom(
                                        geom,
                                        TileBBox(%(zoom)s, %(x)s, %(y)s, 3857)
                                    ) AS geom,
                                    '' AS extent
                                FROM clusters
                                WHERE cid is NULL
                                UNION
                                SELECT NULL as resourceinstanceid,
                                    row_number() over () as id,
                                    count(*) as total,
                                    ST_AsMVTGeom(
                                        ST_Centroid(
                                            ST_Collect(geom)
                                        ),
                                        TileBBox(%(zoom)s, %(x)s, %(y)s, 3857)
                                    ) AS geom,
                                    ST_AsGeoJSON(
                                        ST_Extent(geom)
                                    ) AS extent
                                FROM clusters
                                WHERE cid IS NOT NULL
                                GROUP BY cid
                            ) as tile;""",
                            query_params,
                        )
                    else:
                        # if not full access, add a WHERE clause to only return resources in the valid_resids list
                        cursor.execute(
                            """WITH clusters(tileid, resourceinstanceid, nodeid, geom, cid)
                            AS (
                                SELECT m.*,
                                ST_ClusterDBSCAN(geom, eps := %(distance)s, minpoints := %(min_points)s) over () AS cid
                                FROM (
                                    SELECT tileid,
                                        resourceinstanceid,
                                        nodeid,
                                        geom
                                    FROM geojson_geometries
                                    WHERE nodeid = %(nodeid)s AND resourceinstanceid IN %(valid_resids)s
                                ) m
                            )

                            SELECT ST_AsMVT(
                                tile,
                                %(nodeid),
                                4096,
                                'geom',
                                'id'
                            ) FROM (
                                SELECT resourceinstanceid::text,
                                    row_number() over () as id,
                                    1 as total,
                                    ST_AsMVTGeom(
                                        geom,
                                        TileBBox(%(zoom)s, %(x)s, %(y)s, 3857)
                                    ) AS geom,
                                    '' AS extent
                                FROM clusters
                                WHERE cid is NULL
                                UNION
                                SELECT NULL as resourceinstanceid,
                                    row_number() over () as id,
                                    count(*) as total,
                                    ST_AsMVTGeom(
                                        ST_Centroid(
                                            ST_Collect(geom)
                                        ),
                                        TileBBox(%(zoom)s, %(x)s, %(y)s, 3857)
                                    ) AS geom,
                                    ST_AsGeoJSON(
                                        ST_Extent(geom)
                                    ) AS extent
                                FROM clusters
                                WHERE cid IS NOT NULL
                                GROUP BY cid
                            ) AS tile;""",
                            query_params,
                        )
                else:
                    if full_access is True:
                        # run the basic request and return ALL resources
                        cursor.execute(
                            f"""SELECT ST_AsMVT(tile, %(nodeid)s, 4096, 'geom', 'id') FROM (SELECT tileid,
                                id,
                                resourceinstanceid,
                                nodeid,
                                ST_AsMVTGeom(
                                    geom,
                                    TileBBox(%(zoom)s, %(x)s, %(y)s, 3857)
                                ) AS geom,
                                1 AS total
                            FROM geojson_geometries
                            WHERE nodeid = %(nodeid)s) AS tile;""",
                            query_params
                        )
                    else:
                        # add a WHERE clause to only return resources in the valid_resids list
                        cursor.execute(
                            f"""SELECT ST_AsMVT(tile, %(nodeid)s, 4096, 'geom', 'id') FROM (SELECT tileid,
                                id,
                                resourceinstanceid,
                                nodeid,
                                ST_AsMVTGeom(
                                    geom,
                                    TileBBox(%(zoom)s, %(x)s, %(y)s, 3857)
                                ) AS geom,
                                1 AS total
                            FROM geojson_geometries
                            WHERE nodeid = %(nodeid)s AND resourceinstanceid IN %(valid_resids)s) AS tile;""",
                            query_params
                        )
                tile = bytes(cursor.fetchone()[0])
                cache.set(cache_key, tile, settings.TILE_CACHE_TIMEOUT)

        if not len(tile):
            return self.EMPTY_TILE
        return HttpResponse(tile, content_type="application/x-protobuf")


class ResourceIdLookup(APIBase):

    def get(self, request):

        site_models = [
            "Archaeological Site",
            "Historic Cemetery",
            "Historic Structure"
        ]
        response = {"resources": []}

        for g in Graph.objects.filter(name__in=site_models):

            resources = Resource.objects.filter(graph_id=g.pk)
            for res in resources:
                try:
                    siteid = res.get_node_values("FMSF ID")[0]
                except IndexError:
                    continue
                response['resources'].append((g.name, siteid, res.resourceinstanceid))

        return JSONResponse(response)


################################################################################
################################################################################
# IAN'S ADDITIONS

from arches.app.models.models import Node
from arches.app.models.tile import Tile


# TODO: FIX ME: i am a mutilation of a make_file_list method
def photos_list(resourceid: str) -> list:
    # TODO: make this not a list -- only need one
    resources = []
    id = resourceid

    ## collect resources from arguments
    r = Resource.objects.get(pk=id)
    resources.append(r)

    ## make list of individual resource entries
    output = []
    for res in resources:
        entry = process_resource(res)
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


# TODO: FIX ME: i am a mutilation of a make_file_list method
def process_resource(resource):
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


################################################################################
# IAN'S ENDPOINTS


from fpan.tasks import REPORT_PHOTOS_ZIP_DIR, zip_photos_for_download
from typing import TypedDict, Literal

CeleryTaskState = Literal["PENDING", "STARTED", "RETRY", "FAILURE", "SUCCESS"]


class GetDownloadResponse(TypedDict):
    taskid: str
    task_state: CeleryTaskState
    message: str


def request_report_photos(request: HttpRequest, resourceid: str) -> JSONResponse | HttpResponseBadRequest:
    if request.method != 'GET':
        return HttpResponseBadRequest(b'na')

    # TODO: error handling
    photos = photos_list(resourceid)

    task = zip_photos_for_download.delay(*photos)
    state: CeleryTaskState = task.state

    # TODO: error handling -- how can this fail?
    if state == "FAILURE":
        return JSONResponse(
            GetDownloadResponse(
                taskid="",
                task_state=state,
                message="Failed to start the task. Please try again."
            )
        )

    return JSONResponse(
        GetDownloadResponse(
            taskid=task.id, task_state="", message="Started task."
        )
    )


from pathlib import Path
from celery.result import AsyncResult


class DownloadPhotosStatusResponse(TypedDict):
    taskid: str
    task_state: CeleryTaskState 
    message: str


def get_report_photos(
    request: HttpRequest, taskid: str
) -> FileResponse | JSONResponse | HttpResponseBadRequest:
    if request.method != 'GET':
        return HttpResponseBadRequest(b'na')

    task = AsyncResult(taskid)
    state: CeleryTaskState = task.state

    resp_in_progress = JSONResponse(
        DownloadPhotosStatusResponse(
            taksid=taskid, task_state=task.state, message=""
        )
    )

    match state:
        case "PENDING":
            resp_in_progress["message"] = "Task is queued."
            return resp_in_progress
        case "STARTED":
            resp_in_progress["message"] = "Started."
            return resp_in_progress
        case "RETRY":
            resp_in_progress["message"] = "Retrying."
            return resp_in_progress
        case "FAILURE":
            resp_in_progress["message"] = "Task failed. Please try again."
            return resp_in_progress
        case "SUCCESS":
            filepath = Path(f"{REPORT_PHOTOS_ZIP_DIR}/photos.zip")
            return FileResponse(
                filepath.open("rb"), as_attachment=True, filename=filepath.name
            )

    return HttpResponseBadRequest(
        b"If you see me, we have an unexpected task state."
    )
 
