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
    missing_res_list = []

    def add_arguments(self, parser):
        parser.add_argument("--dry-run",
            action="store_true",
            help='print out old and new values without altering Tiles'
        )
        parser.add_argument("--resourceid",
            help='specify single resourceid to update'
        )

    def handle(self, *args, **options):

        self.region_lookup = {
            "Central": str(ManagementArea.objects.get(name="FPAN Central Region").pk),
            "East Central": str(ManagementArea.objects.get(name="FPAN East Central Region").pk),
            "North Central": str(ManagementArea.objects.get(name="FPAN North Central Region").pk),
            "Northeast": str(ManagementArea.objects.get(name="FPAN Northeast Region").pk),
            "Northwest": str(ManagementArea.objects.get(name="FPAN Northwest Region").pk),
            "Southeast": str(ManagementArea.objects.get(name="FPAN Southeast Region").pk),
            "Southwest": str(ManagementArea.objects.get(name="FPAN Southwest Region").pk),
            "West Central": str(ManagementArea.objects.get(name="FPAN West Central Region").pk), 
        }

        for graph_name in ["Archaeological Site", "Historic Cemetery", "Historic Structure"]:
            self.process_graph(graph_name, dry_run=options['dry_run'], resourceid=options["resourceid"])

        self.report()

    def value_to_pk(self, value_uuid):

        v = Value.objects.get(pk=value_uuid)
        print(f"{value_uuid} --> {v.value}")
        try:
            ma = ManagementArea.objects.get(name=v.value)
        except ManagementArea.DoesNotExist:
            ma = None    
        return ma

    def values_to_strings(self, value_uuid_list):

        if value_uuid_list is None:
            return list()
        if not isinstance(value_uuid_list, list):
            value_uuid_list = [value_uuid_list]
        if len(value_uuid_list) == 0:
            return list()

        outlist = list()
        for value in value_uuid_list:
            v = Value.objects.get(pk=value)
            outlist.append(v.value)
 
        return outlist

    def process_graph(self, graph_name, dry_run=False, resourceid=None):
        print(f"\n -- {graph_name} --")

        g = Graph.objects.get(name=graph_name)

        self.node_lookup = {
            # old nodes
            "Managing Agency": Node.objects.get(name="Managing Agency", graph=g), 
            "Managed Area Name": Node.objects.get(name="Managed Area Name", graph=g),
            "HMS-Region": Node.objects.get(name="HMS-Region", graph=g),
             # new node
            "Management Area": Node.objects.get(name="Management Area", graph=g),
            "Management Agency": Node.objects.get(name="Management Agency", graph=g),
            "FPAN Region": Node.objects.get(name="FPAN Region", graph=g),
            "County": Node.objects.get(name="County", graph=g),
        }

        tiles = Tile.objects.filter(nodegroup_id=self.node_lookup["Managing Agency"].nodegroup)
        tiles_ct = tiles.count()
        print(tiles_ct)

        for n, tile in enumerate(tiles, start=1):
            
            resid = str(tile.resourceinstance_id)
            if resourceid and resid != resourceid:
                continue

            if n % 1000 == 0:
                print(f"{n}, ", end="", flush=True)
            if n == tiles_ct:
                print(f"{n} - done")

            self.process_tile(tile, dry_run=dry_run)
    
    def process_tile(self, tile, dry_run=False):

        resid = str(tile.resourceinstance_id)

        area_old = tile.data.get(str(self.node_lookup["Managed Area Name"].nodeid), [])
        agency_old = tile.data.get(str(self.node_lookup["Managing Agency"].nodeid), [])
        region_old = tile.data.get(str(self.node_lookup["HMS-Region"].nodeid), [])

        area_old_s = self.values_to_strings(area_old)
        agency_old_s = self.values_to_strings(agency_old)
        region_old_s = self.values_to_strings(region_old)

        area_new = self.translate_management_areas(area_old_s, resid)
        agency_new = self.translate_management_agency(agency_old_s)
        region_new = self.translate_region(region_old_s)

        if dry_run is False:

            new_ngid = self.node_lookup["Management Area"].nodegroup_id
            try:
                new_tile = Tile.objects.get(nodegroup_id=new_ngid, resourceinstance_id=resid)
            except Tile.DoesNotExist:
                new_tile = Tile().get_blank_tile_from_nodegroup_id(new_ngid, resourceid=resid)
            
            new_tile.data = {
                str(self.node_lookup["Management Area"].nodeid): area_new,
                str(self.node_lookup["Management Agency"].nodeid): agency_new,
                str(self.node_lookup["FPAN Region"].nodeid): region_new,
                str(self.node_lookup["County"].nodeid): [],
            }
            new_tile.save(log=False)

    def translate_management_areas(self, old_value, resid):

        output = list()
        for ma_name in old_value:
            mas = ManagementArea.objects.filter(name=ma_name)
            if len(mas) >= 1:
                ma = mas[0]
                output.append(str(ma.pk))
                self.matched.update({ma_name: self.matched.get(ma_name, 0) + 1})
            else:
                self.no_match.update({ma_name: self.no_match.get(ma_name, 0) + 1})
                self.missing_res_list.append((ma_name, resid))

        return output

    def translate_management_agency(self, old_value):
        agency_lookup = {
            "FL Dept. of Environmental Protection, Div. of Recreation and Parks": "FSP",
            "FL Dept. of Agriculture and Consumer Services, Florida Forest Service": "FFS",
            "FL Fish and Wildlife Conservation Commission": "FWCC",
            "FL Dept. of Environmental Protection, Florida Coastal Office": "FCO",
            "FL Dept. of Environmental Protection, Office of Water Policy": "OWP",
        }

        return [agency_lookup[i] for i in old_value]

    def translate_region(self, old_value):

        return [self.region_lookup[i] for i in old_value]

    def report(self):

        print(f"matched: {len(self.matched)}")
        print("NO MATCH FOUND:")
        for k, v in self.no_match.items():
            print(f"{k}")
        print(f"unmatched: {len(self.no_match)}")
        print("unmatched details:")
        self.missing_res_list.sort()
        for i in self.missing_res_list:
            print(i)
