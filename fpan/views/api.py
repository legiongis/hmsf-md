from django.core.cache import cache
from django.http import Http404, HttpResponse
from django.db import transaction, connection
from arches.app.models import models
from arches.app.views.api import APIBase
from arches.app.models.system_settings import settings

class MVT(APIBase):
    EARTHCIRCUM = 40075016.6856
    PIXELSPERTILE = 256

    def get(self, request, nodeid, zoom, x, y):
        if hasattr(request.user, "userprofile") is not True:
            models.UserProfile.objects.create(user=request.user)
        viewable_nodegroups = request.user.userprofile.viewable_nodegroups
        try:
            node = models.Node.objects.get(nodeid=nodeid, nodegroup_id__in=viewable_nodegroups)
        except models.Node.DoesNotExist:
            raise Http404()
        config = node.config
        cache_key = f"mvt_{nodeid}_{zoom}_{x}_{y}"
        tile = cache.get(cache_key)
        if tile is None:
            with connection.cursor() as cursor:
                # TODO: when we upgrade to PostGIS 3, we can get feature state
                # working by adding the feature_id_name arg:
                # https://github.com/postgis/postgis/pull/303
                if int(zoom) <= int(config["clusterMaxZoom"]):
                    arc = self.EARTHCIRCUM / ((1 << int(zoom)) * self.PIXELSPERTILE)
                    distance = arc * int(config["clusterDistance"])
                    min_points = int(config["clusterMinPoints"])
                    cursor.execute(
                        """WITH clusters(tileid, resourceinstanceid, nodeid, geom, cid)
                        AS (
                            SELECT m.*,
                            ST_ClusterDBSCAN(geom, eps := %s, minpoints := %s) over () AS cid
                            FROM (
                                SELECT tileid,
                                    resourceinstanceid,
                                    nodeid,
                                    geom
                                FROM mv_geojson_geoms
                                WHERE nodeid = %s
                            ) m
                        )

                        SELECT ST_AsMVT(
                            tile,
                             %s,
                            4096,
                            'geom',
                            'id'
                        ) FROM (
                            SELECT resourceinstanceid::text,
                                row_number() over () as id,
                                1 as total,
                                ST_AsMVTGeom(
                                    geom,
                                    TileBBox(%s, %s, %s, 3857)
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
                                    TileBBox(%s, %s, %s, 3857)
                                ) AS geom,
                                ST_AsGeoJSON(
                                    ST_Extent(geom)
                                ) AS extent
                            FROM clusters
                            WHERE cid IS NOT NULL
                            GROUP BY cid
                        ) as tile;""",
                        [distance, min_points, nodeid, nodeid, zoom, x, y, zoom, x, y],
                    )
                else:
                    cursor.execute(
                        """SELECT ST_AsMVT(tile, %s, 4096, 'geom', 'id') FROM (SELECT tileid,
                            row_number() over () as id,
                            resourceinstanceid,
                            nodeid,
                            ST_AsMVTGeom(
                                geom,
                                TileBBox(%s, %s, %s, 3857)
                            ) AS geom,
                            1 AS total
                        FROM mv_geojson_geoms
                        WHERE nodeid = %s) AS tile;""",
                        [nodeid, zoom, x, y, nodeid],
                    )
                tile = bytes(cursor.fetchone()[0])
                cache.set(cache_key, tile, settings.TILE_CACHE_TIMEOUT)
        if not len(tile):
            raise Http404()
        return HttpResponse(tile, content_type="application/x-protobuf")
