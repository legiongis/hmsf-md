import uuid
from django.core.management.base import BaseCommand, CommandError
from arches.app.models.models import NodeGroup, Node
from arches.app.models.graph import Graph
from arches.app.models.tile import Tile

class Command(BaseCommand):

    help = 'facilitates bulk updates to nodes across the database'

    def add_arguments(self, parser):
        parser.add_argument("node",
            help='specify the name of the node whose values will be updated.'
        )
        parser.add_argument("--set-value",
            help='the value to assign to the nodes.'
        )
        parser.add_argument("--set-empty",
            action="store_true",
            default=False,
            help='set all node values to empty. can be used to initialize '\
                 'newly created nodes. ERASES ALL EXISTING VALUES.'
        )



    def handle(self, *args, **options):

        if options["set_empty"]:
            value = None
        elif options["set_value"]:
            value = options["set_value"]

        try:
            id = uuid.UUID(options["node"])
            nodes = Node.objects.filter(nodeid=id)
        except ValueError:
            nodes = Node.objects.filter(name=options["node"])
        if len(nodes) == 0:
            print("cancelling, no nodes match this name.")
            exit()
        elif len(nodes) > 1:
            print("multiple nodes match this name:")
            for node in nodes:
                print(f"{node.name} - {node.pk} - {node.graph.name}")
            print("\nAll of these nodes will be updated. To choose a specific "\
                  "one, rerun this command using the node id instead of name.")
            if not input("\nproceed? y/N ").lower().startswith("y"):
                print("cancelled")
                exit()

        for node in nodes:

            print(f"{node.name} - {node.pk} - {node.graph.name}")
            tiles = Tile.objects.filter(nodegroup_id=node.nodegroup)

            nodeid = str(node.pk)
            for t in tiles:
                old_value = t.data.get(nodeid, "<no previously saved value>")

                if options["set_empty"] or options["set_value"]:
                    if options["set_empty"]:
                        new_value = None
                    elif options["set_value"]:
                        new_value = options["set_value"]
                    Tile().update_node_value(nodeid, new_value, tileid=t.tileid)
                    print(f"{t.resourceinstance_id}: {old_value} --> {new_value}")
                else:
                    print(f"{t.resourceinstance_id}: {old_value}")

            print(f"  tiles: {tiles.count()}")
