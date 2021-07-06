import os
import csv
import uuid
from datetime import datetime
from django.conf import settings
from django.db.models import CharField
from django.db.models.functions import Lower
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from arches.app.models.models import NodeGroup, Node
from arches.app.models.graph import Graph
from arches.app.models.tile import Tile

class Command(BaseCommand):

    help = '2021 July 5th - this command will set old user id nodes to None if '\
    'they were fully matched during the transfer process. the log from the '\
    'transfer process is used to determine with resources to modify. Also, all'\
    '"waytetwinrivers" variations are retained as requested by kkemp85.'

    def add_arguments(self, parser):
        parser.add_argument("source",
            help='path to CSV with list of resource ids whose nodes should be emptied'
        )

    def handle(self, *args, **options):

        # first get all of the existing tiles for this node group
        # note that both nodes (old and new) are in the same node group, so only
        # one group of tiles is needed.
        old_node = Node.objects.get(name="Visiting Scout ID")
        old_nodeid = str(old_node.nodeid)

        resourceids = {}
        with open(options['source'], "r") as openf:
            reader = csv.reader(openf)
            for row in reader:
                if row[3] == "Full":
                    if "wayte" not in row[1].lower():
                        resourceids[row[0]] = row[1]

        print(f"{len(resourceids)} resources will be updated")

        tiles = Tile.objects.filter(nodegroup_id=old_node.nodegroup)

        ct = 0
        for tile in tiles:
            resid = str(tile.resourceinstance_id)
            if resid not in resourceids.keys():
                continue

            old_value = tile.data.get(old_nodeid, None)
            if not old_value == resourceids[resid]:
                print(old_value)
                print(resourceids[resid])
            Tile().update_node_value(old_nodeid, None, tileid=tile.tileid)
            ct += 1

        print(f"finished, {ct} updated")
