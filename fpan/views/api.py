from __future__ import annotations
import logging
from django.core.cache import cache
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseNotFound,
    HttpResponseServerError
)
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


class DownloadScoutReportPhotos(APIBase):

    def get(self, request):
        """
        Respond with a zip file of photos for a given Scout Report.
        """
        if not (reportid := request.GET.get("rid")):
            return HttpResponseBadRequest(b"Expected url param `rid` (resource id).")

        logger.info("Zipped photos were requested for scout report: " + reportid)

        try:
            zipfile_name, photos = zipped_photos(reportid)
            return FileResponse(
                photos,
                filename=zipfile_name,
                content_type="application/zip",
                as_attachment=True,
            )
        except ValueError as e:
            msg = e
            response = HttpResponseNotFound(msg)
        except OSError as e:
            msg = "Coudn't create the zip file: " + str(e)
            response = HttpResponseServerError(msg)
        except Exception as e:
            msg = "An unexpected error occured when trying to create the zip file: " + str(e)
            response = HttpResponseServerError(msg)

        logger.warning(msg)
        return response


from io import BytesIO


def zipped_photos(reportid: str) -> tuple[str, BytesIO]:
    """
    Returns a tuple containing:
        - zip file name
        - buffer containing a zip file of photos for the provided Scout Report

    Makes synchronous network calls to fetch files from S3.

    Raises:
        ValueError: If resource not found
        LookupError: If resource has no photos
        OSError: If there's an issue reading files or creating the zip
        FileNotFoundError: If a photo file doesn't exist in storage
        MemoryError: If files are too large to fit in memory
    """
    from zipfile import ZipFile
    from arches.app.models.models import File, Node
    from arches.app.models.tile import Tile

    report: Resource
    try:
        report = Resource.objects.get(pk=reportid)
    except Exception as e:
        raise ValueError(
            f"report not found: resource id: {reportid}: {e}"
        ) from e

    # NOTE: Must get photo ids from the tile data.
    # If we get all photo files associated with a resource,
    # we also get photos that were removed from the resource,
    # if they still exist in the `File` table and storage.

    # NOTE: Later, we might want additional tile data for:
    # - Including `Comment` and `Photo Type` node data in the output,
    #     e.g. to be included in a text file in the zipped photos.
    # - Using the display name (tile.photo.name), as opposed to file.path.name.
    #     which includes the true filename on disk/S3, and may differ from the
    #     display name when a file of the same name was previously uploaded.
    # In this case, we'd query the db for `Comment` and `Photo Type` `Nodes`,
    # and use those PKs to get the node data as in:
    # `tile.data.get(str(comment_node.pk))`

    photo_node = Node.objects.get(
        name="Photo", graph__name="Scout Report"
    )
    resource_photo_tiles = Tile.objects.filter(
        nodegroup=photo_node.nodegroup, resourceinstance=report,
    )
    curr_photo_file_ids = [
        photo["file_id"]
        for tile in resource_photo_tiles
        for photo in tile.data.get(str(photo_node.pk))
    ]
    curr_photo_files = File.objects.filter(pk__in=curr_photo_file_ids)

    if not curr_photo_files.exists():
        # should never see this
        # Save Images button only shows when report has photos
        raise LookupError(
            f"Report does not have photos. resource id: {reportid}"
        )

    zip_buf = BytesIO()
    with ZipFile(zip_buf, "w") as zip_file:
        for f in curr_photo_files:
            with f.path.open("rb") as content:
                zip_file.writestr(f.path.name.split("/")[-1], content.read())
    zip_buf.seek(0)

    fmsf_site_id = ""
    fmsf_site_id_node = Node.objects.get(
        name="FMSF Site ID", graph__name="Scout Report"
    )
    fmsf_site_id_tiles = Tile.objects.filter(
        nodegroup=fmsf_site_id_node.nodegroup, resourceinstance=report
    )
    if fmsf_site_id_tiles.exists():
        # filter has results -> must be exactly 1, and the site must exist
        fmsf_site_resourceid = (
            fmsf_site_id_tiles[0].data
            .get(str(fmsf_site_id_node.pk))[0]
            .get("resourceId")
        )
        # site display name = "{id} - {name}"
        fmsf_site_id = (
            Resource.objects.get(pk=fmsf_site_resourceid)
            .displayname()
            .split(" - ", maxsplit=1)[0]
            .strip()
        )

    # report display name = "{report date} - {author,author,...}"
    report_date, report_authors = report.displayname().split(" - ", maxsplit=1)
    report_date = report_date.strip()
    report_authors = "-".join(report_authors.split(","))

    _ = "_"
    zipfile_name = (
        f"photos{_}{fmsf_site_id}{_}{report_date}{_}{report_authors}.zip"
        if fmsf_site_id
        else f"photos{_}{report_date}{_}{report_authors}.zip"
    )

    return zipfile_name, zip_buf
