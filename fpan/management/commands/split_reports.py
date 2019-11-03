import os
import csv
import json
import uuid
from django.core import management
from django.core.management.base import BaseCommand, CommandError
from arches.app.models.system_settings import settings
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
         
        photo_lookup = self.photo_type_conversion()
        exportdir = os.path.join(os.path.dirname(settings.APP_ROOT), "exports")

        resfile = None
        for f in os.listdir(exportdir):
            if f.startswith("resources-with-scout-reports"):
                resfile = os.path.join(exportdir, f)

        if resfile is None:
            print "no resources with scout reports file to split"
            exit()

        print "input file:", resfile

        # load the single exported new Scout Report resource and get information from it
        refdatadir = os.path.join("fpan", "management", "commands", "refdata")
        scoutreport_model = os.path.join(refdatadir, "Scout_Report_2019-08-14_15-46-41.json")
        with open(scoutreport_model, "r") as f:
            data = json.loads(f.read())

        res = data['business_data']['resources'][0]
        newgraphid = res['resourceinstance']['graph_id']
        
        all_nodes = list()
        for t in res['tiles']:
            all_nodes += t['data'].keys()

        nodeidlookup = {
            "f212980f-d534-11e7-8ca8-94659cf754d0": {},
            "73889292-d536-11e7-b3b3-94659cf754d0": {},
            "c67216bf-8cc2-11e7-883c-06ed184dc22c": {},
        }

        for i in set(all_nodes):
            n = Node.objects.get(nodeid=i)
            
            # this is very sloppy, but making three separate sections for the dictionary
            # based on the uuids of the v1 resource models.
            nodeidlookup["f212980f-d534-11e7-8ca8-94659cf754d0"][n.name] = {
                "oldnode":None,
                "newnode":i,
                "oldnodegroupid": None,
                "newnodegroupid": str(n.nodegroup_id),
            }
            nodeidlookup["73889292-d536-11e7-b3b3-94659cf754d0"][n.name] = {
                "oldnode":None,
                "newnode":i,
                "oldnodegroupid": None,
                "newnodegroupid": str(n.nodegroup_id),
            }
            nodeidlookup["c67216bf-8cc2-11e7-883c-06ed184dc22c"][n.name] = {
                "oldnode":None,
                "newnode":i,
                "oldnodegroupid": None,
                "newnodegroupid": str(n.nodegroup_id),
            }

        # here's an output dictionary we'll use to split the input v1 file into multiple
        # files per resource type.
        sorted_v1_resources = {}
        
        # now load the old resource data export from the v1 database
        with open(resfile, "r") as f:
            data = json.loads(f.read())
            
        resources = data['business_data']['resources']

        # iterate the resources until our lookup dictionaries is fully populated
        for rm, subset in nodeidlookup.items():
        
            subresources = [i for i in resources if i['resourceinstance']['graph_id'] == rm]
            
            # put this list in the 
            sorted_v1_resources[rm] = {
                "resources": list(subresources),
                "resourceids": [i['resourceinstance']['resourceinstanceid'] for i in subresources]
            }

            print rm, len(subresources)
            for ct, res in enumerate(subresources):

                for tile in res['tiles']:
                    all_nodes = tile['data'].keys()

                    if None in [v['oldnode'] for k, v in subset.iteritems()]:
                        for nodeid in set(all_nodes):
                                # if not i in [v['oldnode'] for k, v in subset.iteritems()]:
                            nn = Node.objects.get(nodeid=nodeid)
                            # print nn.name
                            if not nn.name in nodeidlookup[rm]:
                                continue
                            subset[nn.name]['oldnode'] = nodeid
                            subset[nn.name]['oldnodegroupid'] = tile['nodegroup_id']

        sr_resources = list()

        for index, res in enumerate(resources):

            oldresid = res['resourceinstance']['resourceinstanceid']
            resgraphid = res['resourceinstance']['graph_id']

            # use the graphid to get the node lookup for this resource model
            subsetlookup = nodeidlookup[resgraphid]

            report_node = Node.objects.get(name="Scout Report", graph_id=res['resourceinstance']['graph_id'])
            report_toptiles = [i for i in res['tiles'] if i['nodegroup_id'] == str(report_node.nodegroup_id)]

            for t in report_toptiles:

                newresid = str(uuid.uuid4())
                newres = {
                    "resourceinstance": {
                        "resourceinstanceid": newresid,
                        "graph_id": newgraphid,
                        "legacyid": newresid,
                    },
                    "tiles": [],
                }

                child_tiles = [i for i in res['tiles'] if i['parenttile_id'] == t['tileid']]
                for ctile in child_tiles:
                    newres['tiles'].append(self.transform_tile(ctile, newresid, subsetlookup, photo_lookup))

                if len(newres['tiles']) > 0:

                    # comment this out if the resources that these reports reference will not be loaded
                    newres['tiles'].append(self.make_resource_instance_tile(newresid, oldresid))

                    sr_resources.append((oldresid, newres))
            if index % 200 == 0:
                print index
            if index % 25 == 0:
                print index,
            elif index == len(resources)-1:
                print index

        for rm, data in sorted_v1_resources.items():

            outv1resfile = rm+".json"
            outresdata = {"business_data": {"resources": data['resources']}}
            outjson = JSONDeserializer().deserialize(JSONSerializer().serialize(JSONSerializer().serializeToPython(outresdata)))

            with open(os.path.join("exports", outv1resfile), "wb") as outf:
                json.dump(outjson, outf, indent=1)

            scout_reports = [s[1] for s in sr_resources if s[0] in data['resourceids']]
            print len(scout_reports)
            outsrfile = rm+"-ScoutReports.json"
            outsrdata = {"business_data": {"resources": scout_reports}}
            outsrjson = JSONDeserializer().deserialize(JSONSerializer().serialize(JSONSerializer().serializeToPython(outsrdata)))
            with open(os.path.join("exports", outsrfile), "wb") as outsrf:
                json.dump(outsrjson, outsrf, indent=1)

        ## export the scout report resources to a new file
        # outfile = "scout-reports"+resfile[-25:]
        # with open(os.path.join(exportdir, outfile), "w") as f:

            # export = JSONDeserializer().deserialize(JSONSerializer().serialize(JSONSerializer().serializeToPython(outbusiness_data)))
            # json.dump(export, f, indent=1)

    def transform_tile(self, intile, resid, subsetlookup, photo_lookup):
        
        nidlookup = {i['oldnode']:i['newnode'] for i in subsetlookup.values()}
        ngidlookup = {i['oldnodegroupid']:i['newnodegroupid'] for i in subsetlookup.values()}
        newtile = {
            "resourceinstance_id": resid, 
            "provisionaledits": None, 
            "parenttile_id": None, 
            "nodegroup_id": ngidlookup[intile['nodegroup_id']], 
            "sortorder": 0, 
            "data": {}, 
            "tileid": str(uuid.uuid4())
        }

        for k, v in intile['data'].items():
            
            nnn = Node.objects.get(nodeid=k)
            if nnn.datatype == "concept-list" and not v is None:
                if not isinstance(v, list):
                    v = [v]
            
            value = self.check_value(v, photo_lookup)
            newtile['data'][nidlookup[k]] = value

        return newtile

    def make_resource_instance_tile(self, resid, otherresid):

        return {
            "data": {
                "a103e68f-bf7f-11e9-aa39-94659cf754d0": otherresid
             }, 
             "provisionaledits": None, 
             "parenttile_id": None, 
             "nodegroup_id": "a103e68f-bf7f-11e9-aa39-94659cf754d0", 
             "sortorder": 0, 
             "resourceinstance_id": resid, 
             "tileid": str(uuid.uuid4())
         }

    def check_value(self, invalue, photo_lookup):

        if invalue is None:
            return None

        # this works because the only list values are dictionaries of uploaded file info
        # and uuids for values.
        if isinstance(invalue, list):
            for val in invalue:
                if isinstance(val, dict):
                    # print val
                    continue
                try:
                    valueobj = Value.objects.get(valueid=val)
                except Value.DoesNotExist as e:
                    print "this is not a valid Value and it's in a list:", val
        else:
            try:
                uuid.UUID(invalue)
                valueobj = Value.objects.get(valueid=invalue)
            except TypeError as e:
                pass
            except ValueError as e:
                pass
            except Value.DoesNotExist as e:
                if invalue in photo_lookup:
                    invalue = photo_lookup[invalue]
                else:
                    print "this is not a valid Value:", invalue

        return invalue


    def photo_type_conversion(self):
        
        v1_dict = {
            "4157929b-6d16-47fd-876f-6b8724a995e8": "Overview", 
            "8b3f3c97-408f-4d99-88b9-df9b7b6eb4cf": "Close-up",
            "fb33287f-8075-4550-97ff-55a1aa131851": "Unique Feature",
            "45e1edf4-7c18-4c1f-8049-26bac2843117": "Close-up",
            "0e133db5-611a-48a7-831d-d3b6bb9bfad8": "Overview",
            "f5e88003-c6dc-428b-a6e4-e107e1eec38b": "Unique Feature",
            "c29a1184-63f0-4669-ad0c-11d680afc765": "Character-defining Feature (Historic Structure only)",
            "4406ed80-6195-418d-9b9b-d955784d0c4f": "Close-up",
            # this is handled explicitly, see comment below
            # "be12ae01-9f49-4b2f-9b57-ffb9b308e88a": "Fa\xc3ade (Historic Structure only)",
            "888ae788-4a40-4c87-8aad-3de83fff9c92": "Overview",
            "dea0f79f-f6ee-454a-bf0f-f27eb98607df": "Unique Feature",
        }

        # hard-code the facade value in here after manually looking it up b/c I don't have
        # time to figure out the encoding issue with the cedille.
        photo_lookup_dict = {
            "be12ae01-9f49-4b2f-9b57-ffb9b308e88a": "12526dfc-aed1-4bf3-a255-6546c9d8177b"
        }
        for k, v in v1_dict.items():
            value = Value.objects.get(value=v)
            photo_lookup_dict[k] = str(value.valueid)

        return photo_lookup_dict