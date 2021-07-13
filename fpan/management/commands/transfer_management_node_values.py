import os
import csv
import uuid
from datetime import datetime
from django.conf import settings
from django.db.models import CharField
from django.db.models.functions import Lower
from django.core.management.base import BaseCommand, CommandError
from arches.app.models.models import NodeGroup, Node, Value
from arches.app.models.graph import Graph
from arches.app.models.tile import Tile

from hms.models import ManagementArea, ManagementAgency

class Command(BaseCommand):

    help = '2021 July 9 - this command supports the transfer of existing '\
        'management area-related nodes to corresponding nodes in the new '\
        'Management branch.'

    matched = {}
    no_match = {}

    def add_arguments(self, parser):
        parser.add_argument("--dry-run",
            action="store_true",
            help='print out old and new values without altering Tiles'
        )
        parser.add_argument("--resourceid",
            help='specify single resourceid to update'
        )

    def handle(self, *args, **options):

        for graph_name in ["Archaeological Site", "Historic Cemetery", "Historic Structure"]:
            self.process_graph(graph_name)

        self.report()

    def value_to_pk(self, value_uuid):

        v = Value.objects.get(pk=value_uuid)
        # print(v.__dict__)
        print(f"{value_uuid} --> {v.value}")
        try:
            ma = ManagementArea.objects.get(name=v.value)
        except ManagementArea.DoesNotExist:
            ma = None    
        return ma

    def process_graph(self, graph_name):

        print(f"\n -- {graph_name} --")

        old_node = Node.objects.get(name="Managed Area Name", graph__name=graph_name)
        old_nodeid = str(old_node.nodeid)
        tiles = Tile.objects.filter(nodegroup_id=old_node.nodegroup)

        tiles_ct = tiles.count()
        print(tiles_ct)

        for n, tile in enumerate(tiles, start=1):
            if n % 1000 == 0:
                print(f"{n}, ", end="", flush=True)
            if n == tiles_ct:
                print(f"{n} - done")
            resid = str(tile.resourceinstance_id)
            old_value = tile.data.get(old_nodeid, None)

            if old_value is not None:
                # if not isinstance(old_value, list):
                #     print(type(old_value))
                #     print(old_value)
                for value_uuid in old_value:

                    area_name = Value.objects.get(pk=value_uuid).value
                    mas = ManagementArea.objects.filter(name=area_name)
                    if len(mas) >= 1:
                        ma = mas[0]
                        self.matched.update({area_name: self.matched.get(area_name, 0) + 1})
                    else:
                        self.no_match.update({area_name: self.no_match.get(area_name, 0) + 1})

    def report(self):

        print("NO MATCH FOUND:")
        for k, v in self.no_match.items():
            print(f"{k}")
        print(f"unmatched: {len(self.no_match)}")
        print(f"matched: {len(self.matched)}")

                # break

            ## split by , then by - and ; to extract names
        #     unames1 = [i.lstrip().rstrip().lower() for i in old_value.split(",")]
        #     unames = []
        #     for un in unames1:
        #         if "-" in un:
        #             unames += un.split("-")
        #         elif ";" in un:
        #             unames += un.split(";")
        #         else:
        #             unames.append(un)
        #
        #     matched_users = []
        #     for uname in unames:
        #         uname = uname.lstrip().rstrip()
        #         if uname in lookups_flat:
        #             uname = lookups_flat[uname]
        #         try:
        #             u = User.objects.get(username__lower=uname)
        #             matched_users.append(u)
        #         except User.DoesNotExist:
        #             if not uname in unmatched:
        #                 unmatched[uname] = 1
        #             else:
        #                 unmatched[uname] += 1
        #
        #     new_value = [str(i.pk) for i in matched_users]
        #     if len(unames) == len(new_value):
        #         match = "Full"
        #         full_matched += 1
        #     elif len(new_value) > 0:
        #         match = "Partial"
        #         partial_matched += 1
        #     else:
        #         unmatched_ct += 1
        #
        #     if options['dry_run'] is True:
        #         print(f"{resid}: {old_value} --> {','.join([str(i.username) for i in matched_users])}")
        #     else:
        #         Tile().update_node_value(new_nodeid, new_value, tileid=tile.tileid)
        #         if match == "Full" and options['erase'] is True:
        #             Tile().update_node_value(old_nodeid, None, tileid=tile.tileid)
        #
        #         rows.append((
        #             resid,
        #             old_value,
        #             ",".join([str(i.username) for i in matched_users]),
        #             match
        #         ))
        #
        # unmatched_frequency = sorted(unmatched.items(), key=lambda x:x[1])
        # for k in unmatched_frequency:
        #     print(k)
        #
        # print(f"full matches: {full_matched}")
        # print(f"partial matches: {partial_matched}")
        # print(f"unmatched: {unmatched_ct}")
        #
        # if len(rows) > 0:
        #     timestamp = datetime.now().strftime("%m-%d-%Y")
        #     filename = f"scout_id_transfer-{timestamp}.csv"
        #     outfile = os.path.join(settings.LOG_DIR, filename)
        #     with open(outfile, "w") as out:
        #         writer = csv.writer(out)
        #         writer.writerows(rows)
