import os
import csv
import json
import uuid
from django.core import management
from django.core.management.base import BaseCommand, CommandError
from arches.app.models.system_settings import settings
from arches.app.utils.data_management.resources.exporter import ResourceExporter
from arches.app.utils.betterJSONSerializer import JSONSerializer, JSONDeserializer
from arches.app.models.resource import Resource
from arches.app.models.models import Node, NodeGroup, Value
from arches.app.models.graph import Graph
from arches.app.models.tile import Tile

class Command(BaseCommand):

    help = 'collects stats needed for FPAN year-end reporting'

    def add_arguments(self, parser):
        pass
        # parser.add_argument("uuid",help='input the uuid string to find')

    def handle(self, *args, **options):

        model_ids = [
            "f212980f-d534-11e7-8ca8-94659cf754d0",
            "73889292-d536-11e7-b3b3-94659cf754d0",
            "c67216bf-8cc2-11e7-883c-06ed184dc22c",
        ]

        exportdir = os.path.join(os.path.dirname(settings.APP_ROOT), "exports")
        exportresids = set()

        for rm_id in model_ids:
            print(rm_id)
            resources = Resource.objects.filter(graph_id=rm_id)
            print(f"total number of resources: {len(resources)}")
            report_node = Node.objects.get(name="Scout Report", graph_id=rm_id)
            report_toptiles = Tile.objects.filter(nodegroup_id=report_node.nodegroup_id)
            print(f"total number of reports: {len(report_toptiles)}")
            resids = set([i.resourceinstance_id for i in report_toptiles])
            exportresids.update(resids)
            resrep = [i for i in resources if i.resourceinstanceid in resids]
            print(f"resources with reports: {len(resrep)}")

        resource_exporter = ResourceExporter('json', single_file=True)
        data = resource_exporter.export(resourceinstanceids=list(exportresids))
        for file in data:
            file['name'] = "resources-with-scout-reports"+file['name'][-25:]
            with open(os.path.join(exportdir, file['name']), 'wb') as f:
                f.write(file['outputfile'].getvalue())