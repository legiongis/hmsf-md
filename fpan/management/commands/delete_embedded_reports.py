import os
import csv
import json
import uuid
from django.core import management
from django.core.management.base import BaseCommand, CommandError
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

        for rm_id in model_ids:
            report_node = Node.objects.get(name="Scout Report", graph_id=rm_id)
            report_toptiles = Tile.objects.filter(nodegroup_id=report_node.nodegroup_id)
            confirm = raw_input("delete {} scout report tiles? Y/n  ".format(len(report_toptiles)))
            if confirm.lower().startswith("n"):
                continue
            for t in report_toptiles:
                t.delete()
