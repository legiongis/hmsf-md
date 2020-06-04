import os
import csv
import uuid
import json
from django.core import management
from django.core.management.base import BaseCommand, CommandError
from django.contrib.gis.geos import GEOSGeometry
from arches.app.utils.betterJSONSerializer import JSONSerializer
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

        # content = self.get_sorted_reports()

        self.make_resource_csvs()

        # resource_models = [
        #     "Archaeological Site",
        #     "Historic Structure",
        #     "Historic Cemetery"
        # ]
        #
        #
        #
        # for rm_name in resource_models:
        #     print(rm_name)
            # graph = Graph.objects.get(name=rm_name)
            # report_node = Node.objects.get(name="Scout Report", graph_id=graph.graphid)
            #
            # report_ng = NodeGroup.objects.get(nodegroupid=report_node.nodegroup_id)
            # report_toptiles = Tile.objects.filter(nodegroup_id=report_ng)
            #
            # resids = [r.resourceinstance_id for r in report_toptiles]



            #self.make_report_csv(rm_name, report_toptiles)

    def load_lookup_table(self):

        refdatadir = os.path.join("fpan", "management", "commands", "refdata")
        path = os.path.join(refdatadir, "FMSF-HMS-lookup-table-2020_05_28.csv")

        lookup = {}
        with open(path, "r") as openf:
            reader = csv.reader(openf)
            next(reader)
            for row in reader:
                lookup[row[2]] = {
                    "resource_model": row[0],
                    "siteid": row[1],
                }
            outdict = {row[2]: row[1] for row in reader}

        return lookup

    # DEPRECATED - This method need not be used anymore, as it's basically covered
    # by the built-in resource export from the search page
    def make_report_csv(self, resource_model, report_toptiles):

        outrows = list()
        node_names = [
            "Visiting Scout ID",
            "Scout Visit Priority Evaluation",
            "Scout Visit Overall Condition",
            "Scout Visit Location Verification",
            "Scout Visit Date",
        ]

        for ct, toptile in enumerate(report_toptiles):
            res = Resource.objects.get(resourceinstanceid=toptile.resourceinstance_id)
            site_id = self.get_node_value(res, "FMSF ID")
            # print 80*"-"
            # print site_id
            report_info = {"FMSF ID": [site_id]}
            children = Tile.objects.filter(parenttile_id=toptile.tileid)
            if len(children) == 0:
                continue
            for c in children:
                for k, v in c.data.items():
                    n = Node.objects.get(nodeid=k)
                    # print n.name
                    if not n.name in node_names:
                        continue

                    if n.name in report_info:
                        report_info[n.name].append(v)
                    else:
                        report_info[n.name] = [v]

            if len(report_info) == 1:
                continue

            outdict = {}
            for k, v in report_info.items():
                transformed = list()
                for i in set(v):
                    try:
                        uuid.UUID(i)
                        transformed.append(Value.objects.get(valueid=i).value)
                    except Exception as e:
                        transformed.append(i)
                outdict[k] = ";".join(transformed)
            outrows.append(outdict)

        outfile = resource_model.lower().replace(" ","-")+"-reports.csv"
        fieldnames = [
            "FMSF ID",
            "Visiting Scout ID",
            "Scout Visit Priority Evaluation",
            "Scout Visit Overall Condition",
            "Scout Visit Location Verification",
            "Scout Visit Date"
        ]
        with open(outfile, "w") as f:
            writer = csv.DictWriter(f, fieldnames)
            writer.writeheader()
            for row in outrows:
                writer.writerow(row)

    def get_sorted_reports(self):

        lookup = self.load_lookup_table()


        all_reports = Resource.objects.filter(graph__name="Scout Report")
        sorted_reports = {
            "Archaeological Site": [],
            "Historic Cemetery": [],
            "Historic Structure": [],
        }

        for sr in all_reports:
            resid = self.get_node_value(sr, "FMSF Site ID")
            if resid in lookup:
                try:
                    res = Resource.objects.get(resourceinstanceid=resid)
                except Resource.DoesNotExist:
                    continue
                item = (sr, res)
                sorted_reports[lookup[resid]["resource_model"]].append(item)

        return sorted_reports

    def make_resource_csvs(self):

        all_reports = Resource.objects.filter(graph__name="Scout Report")
        report_counter = {}
        for sr in all_reports:
            reportid = str(sr.resourceinstanceid)
            resid = self.get_node_value(sr, "FMSF Site ID")
            try:
                res = Resource.objects.get(resourceinstanceid=resid)
            except Resource.DoesNotExist:
                continue
            if res in report_counter:
                report_counter[res] += 1
            else:
                report_counter[res] = 1

        outdict = {
            "Archaeological Site": [],
            "Historic Cemetery": [],
            "Historic Structure": [],
        }

        # because the get_nodes_values method does not work for geospatial nodes
        # yet, we must predetermine the nodeids and get that data through report_toptiles
        geo_nodes = {}
        for rm in list(outdict.keys()):
            graph = Graph.objects.get(name=rm)
            spatial_node = Node.objects.get(name="Geospatial Coordinates",
                                            graph_id=graph)
            geo_nodes[rm] = spatial_node

        for res, ct in report_counter.items():

            name = self.get_node_value(res, "FMSF Name")
            site_id = self.get_node_value(res, "FMSF ID")
            region = self.get_node_value(res, "HMS-Region")
            ownership = self.get_node_value(res, "Ownership")
            area_name = self.get_node_value(res, "Managed Area Name")
            area_cat = self.get_node_value(res, "Managed Area Category")
            agency = self.get_node_value(res, "Managing Agency")
            eval = self.get_node_value(res, "Survey Evaluation")

            row = [str(res.resourceinstanceid), name, site_id, region, ownership,
                area_name, area_cat, agency, eval]

            row.append(ct)

            rn_name = res.graph.name
            if rn_name == "Archaeological Site":
                site_type = self.get_node_value(res, "Site Type")
                row.append(site_type)

            spatial_node = geo_nodes[rn_name]
            try:
                coord_tile = Tile.objects.get(resourceinstance_id=res.resourceinstanceid,
                                              nodegroup_id=spatial_node.nodegroup_id)
                coords = coord_tile.data[str(spatial_node.nodeid)]
                feature = coords['features'][0]
                geom = GEOSGeometry(JSONSerializer().serialize(feature['geometry'])).wkt
            except Tile.DoesNotExist:
                geom = ""

            # put coords at the end
            row.append(geom)

            outdict[rn_name].append(row)

        for resource_model, outrows in outdict.items():
            outfile = resource_model.lower().replace(" ", "-") + "-resource-summary.csv"

            headers = ["resource id", "FMSF name", "FMSF id", "region",
                "ownership", "managed area name", "managed area category", "managing agency",
                "nris eval", "scout reports ct"]
            if resource_model == "Archaeological Site":
                headers.append("archaeological site type")

            # put coords at the end
            headers.append("Coordinates")

            if len(outrows) > 0:
                with open(outfile, "w") as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)
                    [writer.writerow(r) for r in outrows]

    def get_node_value(self, resource, node_name):

        values = resource.get_node_values(node_name)
        if len(values) == 0:
            value = ""
        elif len(values) == 1:
            value = values[0]
        else:
            value = "; ".join(values)

        return value
