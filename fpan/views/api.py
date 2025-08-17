import logging
from django.core.cache import cache
from django.http import Http404, HttpRequest, HttpResponse
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
# Download Report Photos

from typing import TypedDict, Literal
from pathlib import Path

from django.contrib.auth.views import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.http import FileResponse

from celery.result import AsyncResult
from fpan.tasks import REPORT_PHOTOS_ZIP_DIR, zip_photos_for_download

CeleryTaskState = Literal["PENDING", "STARTED", "RETRY", "FAILURE", "SUCCESS"]


class ReportPhotosAPIResponse(TypedDict):
    taskid: str
    task_state: CeleryTaskState
    message: str


# TODO: permissions? CSRF?
# TODO: error handling: make sure rabbitmq server is alive! -- it's currently queueing requests regardless of whether server is available (once server runs, tasks complete)
@method_decorator(csrf_exempt, name='dispatch')  # TEMP
class ReportPhotosAPI(APIBase):
    def post(self, request: HttpRequest):
        """
        Start the background task of zipping the photos associated with a given report [resource] id.
        """
        resourceid = request.POST.get('resourceid')
        task = zip_photos_for_download.delay(resourceid)
        state: CeleryTaskState = task.state

        response = ReportPhotosAPIResponse(
            taskid=task.id,
            task_state=state,
            message="Started task.",
        )

        # TODO: error handling -- how can this fail?
        # TODO: will this accurately reflect a failure? if the rabbitmq server isn't running, state is PENDING
        if state == "FAILURE":
            response["message"] = "Failed to start the task. Please try again."
            return JSONResponse(response)

        return JSONResponse(response)


    def get(self, request: HttpRequest):
        """
        Return the zip file created by `self.post()`.
        """
        taskid = str(request.GET.get("tid"))
        task = AsyncResult(taskid)

        status_response = ReportPhotosAPIResponse(
            taskid=taskid, task_state=task.state, message=""
        )

        state: CeleryTaskState = task.state
        match state:  # exhaustive, except for SUCCESS
            case "PENDING":
                status_response["message"] = "Task is queued."
                return JSONResponse(status_response)
            case "STARTED":
                status_response["message"] = "Started."
                return JSONResponse(status_response)
            case "RETRY":
                status_response["message"] = "Retrying."
                return JSONResponse(status_response)
            case "FAILURE":
                status_response["message"] = "Task failed. Please try again."
                return JSONResponse(status_response)

        # task state is success
        reportid = str(task.get())
        filepath = Path(f"{REPORT_PHOTOS_ZIP_DIR}/{reportid}")
        return FileResponse(
            filepath.open("rb"), as_attachment=True, filename=filepath.name
        )

