import uuid
from django.core.exceptions import ValidationError
from django.contrib.gis.db.models import Model
from arches.app.functions.base import BaseFunction
from arches.app.models import models
from arches.app.models.tile import Tile
from arches.app.models.resource import Resource
from arches.app.models.system_settings import settings
import json
import psycopg2

details = {
    'functionid':'4a1da8f0-dddd-11e7-a700-94659cf754d0',
    'name': 'Instance Permissions Update',
    'type': 'node',
    'description': 'updates the UserXResourceInstanceAccess table',
    'defaultconfig': {"spatial_node_id":"", "inputs":[{"table_field":"","target_node_id":""}] },
    'classname': 'InstancePermissionsUpdate',
    'component': 'views/components/functions/instance_permissions_update'
}

class InstancePermissionsUpdate(BaseFunction):

    def save(self,tile,request):

        ## variable to control verbose output. not hooked into anywhere else in the app,
        ## but useful during development
        verbose = False
        if verbose:
            print(f"verbose: {verbose}")

        ## return early if there is no spatial data to use for a comparison
        spatial_node_id = self.config['spatial_node_id']
        if tile.data[spatial_node_id] == None or tile.data[spatial_node_id] == []:
            ## apparently if there is None in the triggering nodegroup,
            ## an error will occur AFTER this function has returned. So,
            ## for now, setting the value to an empty list to handle this.
            tile.data[spatial_node_id] = []
            return

        ## get geoms from the current tile
        geoms = [feature['geometry'] for feature in tile.data[spatial_node_id]['features']]

        ## create and iterate list of input table/field/target sets
        ## the UI should produce "table_name.field_name" strings

        table_field_targets = self.config['inputs']

        for table_field_target in table_field_targets:
            if verbose:
                print(f"processing input: {table_field_target}")
            ## skip if the table_name.field_name input is not valid
            if not "." in table_field_target['table_field']:
                continue

            ## parse input sets
            table,field = table_field_target['table_field'].split(".")[0],table_field_target['table_field'].split(".")[1]
            target_node_id = table_field_target['target_node_id']
            target_ng_id = models.Node.objects.filter(nodeid=target_node_id)[0].nodegroup_id

            # process each geom and create a list of all values
            vals = []
            for geom in geoms:
                val = attribute_from_postgis(table,field,geom)
                vals+=val
            attributes = list(set(vals))
            if len(attributes) == 0:
                continue

            ## get the datatype of the target node, and if necessary convert the
            ## attributes to value ids. note that prefLabels are expected here,
            ## NOT actual concept ids. what actually gets passed to the tile data
            ## are valueids for the preflabels, not UUIDs for the concept.
            node = models.Node.objects.get(pk=target_node_id)
            target_node_datatype = node.datatype
            if target_node_datatype in ["concept","concept-list"]:
                vals = [get_valueid_from_preflabel(v) for v in attributes]
                attributes = [v for v in vals if v]

            ## if the target node is inside of the currently edited node group,
            ## just set the new value right here
            if str(target_ng_id) == str(tile.nodegroup_id):
                if verbose:
                    print("  inside same nodegroup")
                ## set precedent for correlating new values with target node
                ## datatype. the following will work on a limited basis
                if target_node_datatype == "concept-list":
                    tile.data[target_node_id] = attributes
                elif target_node_datatype == "concept":
                    tile.data[target_node_id] = attributes[0]
                else:
                    tile.data[target_node_id] = attributes[0]

                tile.dirty = False
                continue

            ## if the tile that is to be updated already exists, then it is easy
            ## to find and update it. this should be combined with a
            if verbose:
                print("  checking for previously saved tiles with this target_ng_id")
            previously_saved_tiles = Tile.objects.filter(nodegroup_id=target_ng_id,resourceinstance_id=tile.resourceinstance_id)
            if verbose:
                print(f" {len(previously_saved_tiles)} found")
            if len(previously_saved_tiles) > 0:
                for t in previously_saved_tiles:
                    if target_node_datatype == "concept-list":
                        t.data[target_node_id] = attributes
                    elif target_node_datatype == "concept":
                        t.data[target_node_id] = attributes[0]
                    else:
                        t.data[target_node_id] = attributes[0]
                    t.save()
                continue

            if verbose:
                print("  must need a brand new tile")
            parenttile = Tile().get_blank_tile(target_node_id,resourceid=tile.resourceinstance_id)
            existing_pts = Tile.objects.filter(nodegroup_id=parenttile.nodegroup_id,resourceinstance_id=tile.resourceinstance_id)

            ## if there is no parent tile yet, it should be fine to save the newly created one
            if len(existing_pts) == 0:
                for ng_id,tilelist in parenttile.tiles.iteritems():
                    if ng_id == target_ng_id:
                        if verbose:
                            print("  creating new parent tile and tile")
                        for t in tilelist:
                            if target_node_datatype == "concept-list":
                                t.data[target_node_id] = attributes
                            elif target_node_datatype == "concept":
                                t.data[target_node_id] = attributes[0]
                            else:
                                t.data[target_node_id] = attributes[0]
                parenttile.save()
                continue

            ## if there is one parent tile already, then we need to relate the new tile
            ## to it, and then save the new tile, but not the new parent tile
            if len(existing_pts) == 1:
                for ng_id,tilelist in parenttile.tiles.iteritems():
                    if ng_id == target_ng_id:
                        if verbose:
                            print("  creating new tile and assigning to existing parent tile")
                        for t in tilelist:
                            if target_node_datatype == "concept-list":
                                t.data[target_node_id] = attributes
                            elif target_node_datatype == "concept":
                                t.data[target_node_id] = attributes[0]
                            else:
                                t.data[target_node_id] = attributes[0]
                        t.parenttile = existing_pts[0]
                        t.save()
                        continue

            ## if there are multiple parent tiles already, it's likely that the brand new
            ## one could be saved without any problem (as in len(existing_pts) == 0 above)
            ## but this has not been tested yet.
            if len(existing_pts) > 1:
                if verbose:
                    print("  there are multiple existing parent tiles. this circumstance"\
                        "is not supported at this time.")
                continue

            # tos = Tile.objects.filter(resourceinstance_id=tile.resourceinstance_id)
            # for to in tos:
                # print(to.serialize())
            # print(len(tos))

        return

    def on_import(self):
        print('calling on import')

    def get(self):
        print('calling get')

    def delete(self):
        print('calling delete')
