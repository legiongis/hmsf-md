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
            '-i',
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
            for k, v in settings.SPATIAL_JOIN_GRAPHID_LOOKUP.items():
                print(k)
                tiles = Tile.objects.filter(nodegroup_id=v['Nodegroup'])
                empty_tiles = [i for i in tiles if i.data and not i.data[v["FPAN Region"]]]
                print(f"resources to join: {len(empty_tiles)}")
                resids += [i.resourceinstance.pk for i in empty_tiles]
            resources = ResourceInstance.objects.filter(pk__in=resids)
            print(f"\ntotal resources: {resources.count()}")
            if not options["noinput"]:
                if input("continue? Y/n").lower().startswith("n"):
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
