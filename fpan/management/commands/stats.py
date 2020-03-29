import os
import csv
import json
from django.core import management
from django.core.management.base import BaseCommand, CommandError
from arches.app.models.resource import Resource
from arches.app.models.models import Node, NodeGroup
from arches.app.models.graph import Graph
from arches.app.models.tile import Tile

class Command(BaseCommand):

    help = 'collects stats needed for FPAN year-end reporting'

    def add_arguments(self, parser):
        pass
        # parser.add_argument("uuid",help='input the uuid string to find')

    def handle(self, *args, **options):

        report_nodes = Node.objects.filter(name="Scout Report")

        for node in report_nodes:
            graph = Graph.objects.get(graphid=node.graph_id)
            if graph.name == "Scout Report":
                continue
            print(graph.name)
            report_ng = NodeGroup.objects.get(nodegroupid=node.nodegroup_id)
            report_tiles = Tile.objects.filter(nodegroup_id=report_ng)
            resources = [r.resourceinstance_id for r in report_tiles]
            
            print(f"total reports: {len(report_tiles)}")
            print(f"resource count: {len(set(resources))}")
            for tile in report_tiles:
                child_tiles = Tile.objects.filter(parenttile_id=tile.tileid)