import logging
from psycopg2 import sql
from django.core.cache import cache
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.db import transaction, connection
from django.db.utils import IntegrityError
from arches.app.models import models
from arches.app.views.api import APIBase
from arches.app.models.system_settings import settings
from arches.app.models.resource import Resource
from arches.app.models.graph import Graph
from arches.app.utils.response import JSONResponse

from hms.models import UserXResourceInstanceAccess
from fpan.search.components.site_filter import SiteFilter

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
            # if rules["access_level"] == "geo_filter":
            #     geom = rules["geometry"]
            #     # ST_SetSRID({geom}, 4236)
            #     resid_where = f"ST_Intersects(geom, ST_Transform('{geom}', 3857))"

            access_info = SiteFilter().get_rules(request.user, str(node.graph_id))
            if access_info["access_level"] == "full_access":
                # set extra where clause to match everything
                resid_where = "NULL IS NULL"
            elif access_info["access_level"] == "no_access":
                return self.EMPTY_TILE
            else:
                resids = UserXResourceInstanceAccess.objects.filter(
                        user=request.user,
                        resource__graph_id=str(node.graph_id),
                    ).values_list("resource__resourceinstanceid", flat=True)
                if len(resids) == 0:
                    return self.EMPTY_TILE
                resid_str = "','".join([str(i) for i in ok])
                resid_where = f"resourceinstanceid IN ('{resid_str}')"

            with connection.cursor() as cursor:

                query_params = {
                    'nodeid': nodeid,
                    'zoom': zoom,
                    'x': x,
                    'y': y,
                    'resid_where': resid_where,
                }

                if int(zoom) <= int(config["clusterMaxZoom"]):
                    arc = self.EARTHCIRCUM / ((1 << int(zoom)) * self.PIXELSPERTILE)
                    distance = arc * int(config["clusterDistance"])
                    min_points = int(config["clusterMinPoints"])

                    query_params['distance'] = distance
                    query_params['min_points'] = min_points

                    cursor.execute(
                        """WITH clusters(tileid, resourceinstanceid, nodeid, geom, cid)
                        AS (
                            SELECT m.*,
                            ST_ClusterDBSCAN(geom, eps := {distance}, minpoints := {min_points}) over () AS cid
                            FROM (
                                SELECT tileid,
                                    resourceinstanceid,
                                    nodeid,
                                    geom
                                FROM mv_geojson_geoms
                                WHERE nodeid = '{nodeid}' AND {resid_where}
                            ) m
                        )

                        SELECT ST_AsMVT(
                            tile,
                             '{nodeid}',
                            4096,
                            'geom',
                            'id'
                        ) FROM (
                            SELECT resourceinstanceid::text,
                                row_number() over () as id,
                                1 as total,
                                ST_AsMVTGeom(
                                    geom,
                                    TileBBox({zoom}, {x}, {y}, 3857)
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
                                    TileBBox({zoom}, {x}, {y}, 3857)
                                ) AS geom,
                                ST_AsGeoJSON(
                                    ST_Extent(geom)
                                ) AS extent
                            FROM clusters
                            WHERE cid IS NOT NULL
                            GROUP BY cid
                        ) as tile;""".format(**query_params)
                    )
                else:
                    cursor.execute(
                        """SELECT ST_AsMVT(tile, '{nodeid}', 4096, 'geom', 'id') FROM (SELECT tileid,
                            row_number() over () as id,
                            resourceinstanceid,
                            nodeid,
                            ST_AsMVTGeom(
                                geom,
                                TileBBox({zoom}, {x}, {y}, 3857)
                            ) AS geom,
                            1 AS total
                        FROM mv_geojson_geoms
                        WHERE nodeid = '{nodeid}' AND {resid_where}) AS tile;""".format(**query_params)
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
