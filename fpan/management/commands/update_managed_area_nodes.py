from django.core.management.base import BaseCommand, CommandError
from arches.app.models.models import Node, NodeGroup, Value, Concept
from arches.app.models.tile import Tile
from arches.app.models.concept import Concept as NonORMConcept

class Command(BaseCommand):

    help = 'bulk addition of user accounts from a csv file'

    def add_arguments(self, parser):
        # parser.add_argument("--csv_file", default=None,
            # help='path to the csv holding the names of the accounts to add')
        # parser.add_argument("--land_managers", action="store_true", default=False,
            # help='specify whether the full complement of state land manager accounts should be created')
        # parser.add_argument("--mock_scouts", action="store_true", default=False,
            # help='specify whether some mock scout accounts should be created')
        # parser.add_argument("--fake_passwords", action="store_true", default=False,
            # help='use fake passwords for testing: passwords for state land entities will match the username')
        pass

    def handle(self, *args, **options):

        self.update_nodes()

    def update_nodes(self):
        '''this function should be run on a fully populated HMS v1 database. It will accomplish the
        following things:
            1. Change the Managed Area Category node to concept-list and attach the
               Managed Area collection to it
            2. Update the existing Managed Area Category tiles in place to use the new concepts
               for each managed area instead of the existing strings.
        '''
        
        ma_cat_coll, ma_coll = False, False
        collection_nodes = Concept.objects.filter(nodetype_id="Collection")
        for cn in collection_nodes:
            labels = NonORMConcept().get(cn.conceptid).values
            if "Managing Agency" in [l.value for l in labels]:
                ma_coll = cn
            if "Managed Area Category" in [l.value for l in labels]:
                ma_cat_coll = cn

        self.convert_managed_area_category_nodes(ma_cat_coll)
        self.convert_managing_agency_nodes(ma_coll)

    def convert_managed_area_category_nodes(self, collection):

        # get the real category nodes (they will be used to find the tiles)
        ma_cat_nodes = Node.objects.filter(name="Managed Area Category")

        for n in ma_cat_nodes:

            # alter the datatype of the node and assign the RDM collection
            n.datatype = "concept-list"
            n.config = {"rdmCollection":str(collection.conceptid)}
            n.save()
            print n.__dict__

            # now find and convert all existing values for this node
            # ng = NodeGroup.objects.get(nodegroupid=n.nodegroup_id)
            # print ng.__dict__
            tiles = Tile.objects.filter(nodegroup_id=n.nodegroup_id)
            print "modifying {} tiles".format(len(tiles))
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
                    print "ERROR:", exval
                    continue
                t.data[str(n.nodeid)] = [str(newval)]
                t.save()

    def convert_managing_agency_nodes(self, collection):

        # get the real category nodes (they will be used to find the tiles)
        ma_nodes = Node.objects.filter(name="Managing Agency")

        for n in ma_nodes:

            # alter the datatype of the node and assign the RDM collection
            n.datatype = "concept-list"
            n.config = {"rdmCollection":str(collection.conceptid)}
            n.save()
            print n.__dict__

            # now find and convert all existing values for this node
            # ng = NodeGroup.objects.get(nodegroupid=n.nodegroup_id)
            # print ng.__dict__
            tiles = Tile.objects.filter(nodegroup_id=n.nodegroup_id)
            print "modifying {} tiles".format(len(tiles))
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