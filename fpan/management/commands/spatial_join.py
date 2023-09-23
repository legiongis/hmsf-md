import os
import csv
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from arches.app.models.models import ResourceInstance
from arches.app.models.graph import Graph

from fpan.utils import SpatialJoin
from fpan.tasks import run_full_spatial_join

class Command(BaseCommand):

    help = 'export all of the FMSF site ids from resources in the database'

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
            '--background',
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
        else:
            exit()

        joiner = SpatialJoin()
        for res in resources:
            print(res)
            joiner.update_resource(res)