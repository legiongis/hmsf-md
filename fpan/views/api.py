import logging
from django.core.cache import cache
from django.http import FileResponse, Http404, HttpResponse, HttpResponseNotFound, HttpResponseServerError
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


from pathlib import Path

# NOTE: neither Django nor Arches' `MEDIA_ROOT`s point to "fpan/fpan"
from fpan.settings import MEDIA_ROOT

REPORT_PHOTOS_ZIP_DIR = Path(MEDIA_ROOT + "/report_photo_downloads")
REPORT_PHOTOS_SOURCE_DIR = Path(MEDIA_ROOT + "/uploadedfiles")


class DownloadScoutReportPhotos(APIBase):

    def get(self, request):
        if not (reportid := request.GET.get("rid", None)):
            return HttpResponseNotFound(b"Expected url param `rid`.")

        logger.info("Zipped photos were requested for scout report: " + reportid)

        try:
            zipfile_path = Path(zip_photos_for_download(reportid))
            return FileResponse((REPORT_PHOTOS_ZIP_DIR / zipfile_path).open("rb"))
        except ValueError as e:
            msg = e
        except OSError as e:
            msg = "Coudn't create the zip file: " + str(e)
        except Exception as e:
            msg = "An unexpected error occured when trying to create the zip file: " + str(e)

        logger.warning(msg)
        return HttpResponseServerError(msg)


# TODO: where will we store zip downloads?
# TODO: swap local source dir for S3 bucket && update file zipping logic

def zip_photos_for_download(reportid) -> Path:
    """
    Gathers photos related to `reportid`, zip them, and return a `Path` object
    representing the zip file.

    Raises an `OSError` via `ZipFile.write()` if there's an issue writing the file.
    """
    from zipfile import ZipFile

    photo_filenames = photos_list(reportid)

    zipfile_path = REPORT_PHOTOS_ZIP_DIR / f"report-photos-{reportid}.zip"

    # add parent dirs of dest dir if needed (like bash mkdir)
    zipfile_path.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(zipfile_path, "w") as zip_file:
        for filename in photo_filenames:
            photo_path = Path(REPORT_PHOTOS_SOURCE_DIR / filename)
            zip_file.write(photo_path, arcname=filename)

    return zipfile_path


# TODO: TEST ME
#     - what if there are no photos?
def photos_list(resourceid: str) -> list[str]:
    try:
        r = Resource.objects.get(pk=resourceid)
    except Exception as e:
        raise ValueError(f"resource not found: resource id: {resourceid}: {e}")
    r = processed_resource(r)
    photo_filenames = r["file_data"].get("Photo")
    if photo_filenames is None:
        raise ValueError(f"Resource does not have photos. resource id: {resourceid}")
    return photo_filenames


# TODO: TEST ME
#     - what if there are no photos?
def processed_resource(resource):
    from arches.app.models.models import Node
    from arches.app.models.tile import Tile

    ## get all file-list nodes for this resource's graph
    nodes = Node.objects.filter(datatype="file-list", graph__name=resource.graph.name)

    ## create lookup of node id to node name (to use later)
    node_lookup = {str(i.pk): i.name for i in nodes}

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
