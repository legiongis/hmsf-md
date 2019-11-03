from django.core.management.base import BaseCommand, CommandError
from arches.app.models.models import Node, NodeGroup, Value, Concept
from arches.app.models.graph import Graph
from arches.app.models.tile import Tile
from arches.app.models.concept import Concept as NonORMConcept

RESOURCE_TO_USE = "f1575fda-6983-4a77-a016-5021dab7697d"

class Command(BaseCommand):

    help = 'bulk addition of user accounts from a csv file'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):

        self.update_nodes()

    def update_nodes(self):
        '''this function should be run on a fully populated HMS v1 database. It will accomplish the
        following things:
            1. Change the Managed Area Category, Managing Agency, and Managed Area Name nodes
               to concept-list and attach appropriate collection to the updated node.
            2. Update the existing Managed Area Category, Managing Agency, and Managed Area Name
               tiles in place to use the new conceptsfor each managed area instead of the existing
               string values in those tiles.
        '''
        
        self.set_nodes_to_concept_list()
        self.convert_tile_values()

    def convert_tile_values(self):
        
        cat_nodes = Node.objects.filter(name="Managed Area Category")
        cat_nodeids = [str(i.nodeid) for i in cat_nodes]
        ma_nodes = Node.objects.filter(name="Managing Agency")
        ma_nodeids = [str(i.nodeid) for i in ma_nodes]
        man_nodes = Node.objects.filter(name="Managed Area Name")
        man_nodeids = [str(i.nodeid) for i in man_nodes]
        
        allnodeids = cat_nodeids + ma_nodeids + man_nodeids
        nodes = list(cat_nodes) + list(ma_nodes) + list(man_nodes)
        ngs = list(set([i.nodegroup_id for i in nodes]))
        
        for ngid in ngs:
            ng = NodeGroup.objects.get(nodegroupid=ngid)
            tiles = Tile.objects.filter(nodegroup_id=ng.nodegroupid)
            if tiles.count() == 0:
                continue
            print("GRAPH: " + str(tiles[0].resourceinstance_id))
            print(str(len(tiles))+ " tiles to update")
            for i, t in enumerate(tiles):

                for k, v in t.data.items():

                    if v is None or k not in allnodeids:
                        continue

                    if v == "State Park":
                        ## this is where the region spreadsheets will need to be referenced,
                        ## to put this site in a state park region. For now just make the
                        ## slight change so that it fits the existing label in the RDM
                        v = "State Parks"

                    try:
                        newval = Value.objects.get(value=v).valueid
                    except Value.DoesNotExist:
                        print("ERROR: {} RESOURCE ID: {}".format(str(v), t.resourceinstance_id))
                        continue

                    t.data[k] = [str(newval)]

                t.save(log=False)
                
                if i % 500 == 0:
                    print i
                elif i % 50 == 0:
                    print i,

                
    def set_nodes_to_concept_list(self):
        
        cat_coll, ma_coll, man_coll = None, None, None
        collections = Concept.objects.filter(nodetype_id="Collection")
        for cn in collections:
            labels = NonORMConcept().get(cn.conceptid).values
            if "Managed Area Category" in [l.value for l in labels]:
                cat_coll = cn
            elif "Managing Agency" in [l.value for l in labels]:
                ma_coll = cn
            elif "Managed Area Name" in [l.value for l in labels]:
                man_coll = cn

        ma_cat_nodes = Node.objects.filter(name="Managed Area Category")
        for n in ma_cat_nodes:
            n.datatype = "concept-list"
            n.config = {"rdmCollection":str(cat_coll.conceptid)}
            n.save()

        ma_nodes = Node.objects.filter(name="Managing Agency")
        for n in ma_nodes:
            n.datatype = "concept-list"
            n.config = {"rdmCollection":str(ma_coll.conceptid)}
            n.save()

        man_nodes = Node.objects.filter(name="Managed Area Name")
        for n in man_nodes:
            n.datatype = "concept-list"
            n.config = {"rdmCollection":str(man_coll.conceptid)}
            n.save()

        # would probably be best to instantiate the graph objects here
        # and save it right away. I think the change of node triggers a card change
        # that needs to be explicitly saved.
        #for g in Graph.objects.all():
            #g.save()

    def reset_nodes_to_string(self):

        cat_nodes = Node.objects.filter(name="Managed Area Category")
        ma_nodes = Node.objects.filter(name="Managing Agency")
        man_nodes = Node.objects.filter(name="Managed Area Name")
        
        for nodeset in [cat_nodes, ma_nodes, man_nodes]:
            for n in nodeset:
                n.datatype = 'string'
        # if not n.datatype == "concept-list":
            # n.datatype = "concept-list"
            # n.config = {"rdmCollection":str(collection.conceptid)}
                n.save()