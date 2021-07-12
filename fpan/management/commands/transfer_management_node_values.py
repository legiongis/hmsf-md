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

class Command(BaseCommand):

    help = '2021 July 9 - this command supports the transfer of existing '\
        'management area-related nodes to corresponding nodes in the new '\
        'Management branch.'

    def add_arguments(self, parser):
        parser.add_argument("--dry-run",
            action="store_true",
            help='print out old and new values without altering Tiles'
        )
        parser.add_argument("--resourceid",
            help='specify single resourceid to update'
        )

    def handle(self, *args, **options):

        self.process()

    def value_to_pk(self, value_uuid):

        v = Value.objects.get(pk=value_uuid)
        mas = ManagementArea.objects.filter(name=v.label)
        print(mas)

    def process(self):

        # first get all of the existing tiles for this node group
        # note that both nodes (old and new) are in the same node group, so only
        # one group of tiles is needed.
        old_node = Node.objects.get(name="Managed Area Name", graph__name="Archaeological Site")
        old_nodeid = str(old_node.nodeid)
        tiles = Tile.objects.filter(nodegroup_id=old_node.nodegroup)

        print(tiles.count())

        # new_node = Node.objects.get(name="Scout ID(s)")
        # new_nodeid = str(new_node.nodeid)
        #
        # full_matched = 0
        # partial_matched = 0
        # unmatched_ct = 0
        # unmatched = {}
        # rows = [
        #     ("resourceid", "original_value", "matching_usernames", "match")
        # ]
        print()

        for tile in tiles:
            print("%%%%")
            resid = str(tile.resourceinstance_id)
            print(resid)
            # if options['resourceid'] and resid != options['resourceid']:
            #     continue

            old_value = tile.data.get(old_nodeid, None)
            if old_value is None:
                old_value = ""
            print(old_value)
            break

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
