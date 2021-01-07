from arches.app.models.system_settings import settings
from arches.app.models.models import Node, NodeGroup
from arches.app.models.resource import Resource
from arches.app.models.graph import Graph
from arches.app.models.tile import Tile

# place to stash tiny helper utils needed in different parts of the app


weekday_lookup = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}


def get_node_value(resource, node_name):

    values = resource.get_node_values(node_name)
    if len(values) == 0:
        value = ""
    elif len(values) == 1:
        value = values[0]
    else:
        value = "; ".join(values)

    return value

def get_inline_resources(resourceid):

    resource = Resource.objects.get(resourceinstanceid=resourceid)
    graph = resource.graph

    inline_config = settings.REPORT_INLINES
    inline_output = []

    if graph.name in inline_config:

        # per resource model, there may be multiple inline defined
        model_level_data = {
            "graph_name": graph.name,
            "inlines": []
        }

        # iterate the inlines defined for this resource model, and collect
        # all of the resources that match it.
        for inline_info in inline_config[graph.name]:

            # ultimately, for each inline there will be a node name and a list of resources
            collected_data = {
                "node_name": inline_info['node_to_look_in'],
            }

            # the graph of the resource model that stores the resource-instance node information
            # that may match this resource's resource id
            inline_model = Graph.objects.get(name=inline_info['inline_model'])

            # the specific node that holds the resource instance data. this must be a resource-instance node.
            inline_node = Node.objects.get(graph=inline_model, name=inline_info['node_to_look_in'])

            # the nodegroup for the node defined above. this is needed because tiles have nodegroupids,
            # not node ids (though the node ids are in the tile.data.keys())
            inline_ng = NodeGroup.objects.get(nodegroupid=inline_node.nodegroup_id)

            # get all tiles matching the nodegroupd
            inline_tiles = Tile.objects.filter(nodegroup=inline_ng)

            # for all of the tiles, if the this resource's resourceinstanceid is in the tile.data.values(),
            # then add the resourceinstance_id of the tile that contains this value.
            inline_resids = [str(t.resourceinstance_id) for t in inline_tiles if resourceid in t.data.values()]

            # get the list of resources, both the resourceinstanceid and display name for each
            resources = list()
            for resid in inline_resids:
                res = Resource.objects.get(resourceinstanceid=resid)
                resources.append({"resid": resid, "displayname": res.displayname})

            # sort the resources by name and add them to the collected data object
            collected_data['resources'] = sorted(resources, key=lambda k: k['displayname'])
            model_level_data['inlines'].append(collected_data)

        inline_output.append(model_level_data)

    return inline_output
