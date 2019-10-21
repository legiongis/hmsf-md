from django.core.management.base import BaseCommand, CommandError
from arches.app.models.models import Node, NodeGroup, Value, Concept
from arches.app.models.tile import Tile
from arches.app.models.concept import Concept as NonORMConcept

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

        self.convert_managed_area_category_nodes("Managed Area Category")
        self.convert_nodes_and_update_tiles("Managing Agency")
        self.convert_nodes_and_update_tiles("Managed Area Name")

    def convert_managed_area_category_nodes(self, collection_name):
        '''this is essentially the same as convert_nodes_and_update_tiles() below,
        but is kept separate at this time becuase additional logic will need to be
        added to handle the new State Park regional grouping.'''
        
        collection_nodes = Concept.objects.filter(nodetype_id="Collection")
        for cn in collection_nodes:
            labels = NonORMConcept().get(cn.conceptid).values
            if collection_name in [l.value for l in labels]:
                collection = cn

        # get the real category nodes (they will be used to find the tiles)
        ma_cat_nodes = Node.objects.filter(name="Managed Area Category")

        for n in ma_cat_nodes:

            # alter the datatype of the node and assign the RDM collection
            n.datatype = "concept-list"
            n.config = {"rdmCollection":str(collection.conceptid)}
            n.save()

            # now find and convert all existing values for this node
            # ng = NodeGroup.objects.get(nodegroupid=n.nodegroup_id)
            # print ng.__dict__
            tiles = Tile.objects.filter(nodegroup_id=n.nodegroup_id)
            print("modifying {} tiles".format(len(tiles)))
            for t in tiles:
                exval = t.data[str(n.nodeid)]
                if exval is None:
                    continue
                if exval == "State Park":
                    ## this is where the region spreadsheets will need to be referenced,
                    ## to put this site in a state park region. For now just make the
                    ## slight change so that it fits the existing label in the RDM
                    exval = "State Parks"
                try:
                    newval = Value.objects.get(value=exval).valueid
                except Value.DoesNotExist:
                    print("ERROR: " + exval)
                    continue
                t.data[str(n.nodeid)] = [str(newval)]
                t.save()

    def convert_nodes_and_update_tiles(self, collection_name):
    
        collection_nodes = Concept.objects.filter(nodetype_id="Collection")
        for cn in collection_nodes:
            labels = NonORMConcept().get(cn.conceptid).values
            if collection_name in [l.value for l in labels]:
                collection = cn

        # get the real category nodes (they will be used to find the tiles)
        ma_nodes = Node.objects.filter(name=collection_name)

        for n in ma_nodes:

            # alter the datatype of the node and assign the RDM collection
            n.datatype = "concept-list"
            n.config = {"rdmCollection":str(collection.conceptid)}
            n.save()

            # now find and convert all existing values for this node
            # ng = NodeGroup.objects.get(nodegroupid=n.nodegroup_id)
            # print ng.__dict__
            tiles = Tile.objects.filter(nodegroup_id=n.nodegroup_id)
            print("modifying {} tiles".format(len(tiles)))
            for t in tiles:
                exval = t.data[str(n.nodeid)]
                if exval is None:
                    continue
                try:
                    newval = Value.objects.get(value=exval).valueid
                except Value.DoesNotExist:
                    print "ERROR:", exval
                    continue
                t.data[str(n.nodeid)] = [str(newval)]
                t.save()