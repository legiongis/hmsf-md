import os
import csv
from datetime import datetime
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from arches.app.models.models import ResourceInstance
from arches.app.models.graph import Graph
from arches.app.models.tile import Tile

from fpan.utils import SpatialJoin
from fpan.tasks import run_full_spatial_join

class Command(BaseCommand):

    help = "Performs a spatial join between the management areas and resources"

    def add_arguments(self, parser):
        parser.add_argument(
            '-r',
            '--resourceinstanceid',
        )
        parser.add_argument(
            '--all',
            action="store_true",
        )
        parser.add_argument(
            '--backfill',
            action="store_true",
        )
        parser.add_argument(
            '--background',
            action="store_true",
        )
        parser.add_argument(
            '--noinput',
            action="store_true",
        )

    def handle(self, *args, **options):

        resid = options['resourceinstanceid']
        if resid:
            resources = ResourceInstance.objects.filter(pk=resid)
        elif options['all']:
            if options['background']:
                print("running in the background")
                run_full_spatial_join.delay()
                exit()
            resources = ResourceInstance.objects.filter(graph__name__in=[
                "Archaeological Site",
                "Historic Cemetery",
                "Historic Structure",
            ])
        elif options["backfill"]:
            # find all empty FPAN Region nodes and use only these resources
            resids = []
            for k, v in settings.SPATIAL_JOIN_NODE_LOOKUP.items():
                print(k)
                all_tiles = Tile.objects.filter(nodegroup_id=v['nodegroupid'])
                res_with_nodegroup = all_tiles.values_list("resourceinstance_id", flat=True)
                res_without_nodegroup = ResourceInstance.objects.filter(graph__name=k).exclude(pk__in=res_with_nodegroup)
                resids_missing_region = list(res_without_nodegroup.values_list("pk", flat=True))
                for tile in all_tiles:
                    if tile.data:
                        ## use the FPAN Region as a way to test whether this has been filled.
                        region_val = tile.data.get(v["region_nodeid"])
                        if region_val in (None, ""):
                            resids_missing_region.append(tile.resourceinstance.pk)
                print(f"resources to join: {len(resids_missing_region)}")
                print(resids_missing_region[:25])
                resids += resids_missing_region
            resources = ResourceInstance.objects.filter(pk__in=resids)
            print(f"\ntotal resources: {resources.count()}")
            if resources.count() == 0:
                exit()
            if not options["noinput"]:
                if input("continue? Y/n ").lower().startswith("n"):
                    exit()
        else:
            exit()

        joiner = SpatialJoin()
        total = resources.count()
        start = datetime.now()
        for n, res in enumerate(resources, start=1):
            print(f'{n}/{total}: {str(res.pk)} ({res.graph.name})')
            joiner.update_resource(res)
        print(f"completed. elapsed time: {datetime.now() - start}")
