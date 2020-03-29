import json
from django.shortcuts import render, Http404

from arches.app.models import models
from arches.app.models.system_settings import settings
from arches.app.models.resource import Resource
from arches.app.models.tile import Tile
from arches.app.models.graph import Graph
from arches.app.models.card import Card
from arches.app.utils.betterJSONSerializer import JSONSerializer, JSONDeserializer
from arches.app.views.resource import ResourceReportView

from fpan.utils.permission_backend import user_can_edit_this_resource


class FPANResourceReportView(ResourceReportView):


    def get_inline_resources(self, graph, resourceid):

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
                inline_node = models.Node.objects.get(graph=inline_model, name=inline_info['node_to_look_in'])

                # the nodegroup for the node defined above. this is needed because tiles have nodegroupids,
                # not node ids (though the node ids are in the tile.data.keys())
                inline_ng = models.NodeGroup.objects.get(nodegroupid=inline_node.nodegroup_id)

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

    def get(self, request, resourceid=None):

        if not user_can_edit_this_resource(request.user, resourceid):
            raise Http404

        # manually update the settings here
        # before adding this line, the mapbox key was not available in the report, for example.
        settings.update_from_db()

        lang = request.GET.get('lang', settings.LANGUAGE_CODE)
        resource = Resource.objects.get(pk=resourceid)
        displayname = resource.displayname
        resource_models = models.GraphModel.objects.filter(isresource=True).exclude(
            isactive=False).exclude(pk=settings.SYSTEM_SETTINGS_RESOURCE_MODEL_ID)

        tiles = Tile.objects.filter(resourceinstance=resource).order_by('sortorder')

        graph = Graph.objects.get(graphid=resource.graph_id)
        cards = Card.objects.filter(graph=graph).order_by('sortorder')
        permitted_cards = []
        permitted_tiles = []

        perm = 'read_nodegroup'

        inlines = self.get_inline_resources(graph, resourceid)

        for card in cards:
            if request.user.has_perm(perm, card.nodegroup):
                card.filter_by_perm(request.user, perm)
                permitted_cards.append(card)

        for tile in tiles:
            if request.user.has_perm(perm, tile.nodegroup):
                tile.filter_by_perm(request.user, perm)
                permitted_tiles.append(tile)


        try:
            map_layers = models.MapLayer.objects.all()
            map_markers = models.MapMarker.objects.all()
            map_sources = models.MapSource.objects.all()
            geocoding_providers = models.Geocoder.objects.all()
        except AttributeError:
            raise Http404(_("No active report template is available for this resource."))

        cardwidgets = [widget for widgets in [card.cardxnodexwidget_set.order_by(
            'sortorder').all() for card in permitted_cards] for widget in widgets]

        datatypes = models.DDataType.objects.all()
        widgets = models.Widget.objects.all()
        templates = models.ReportTemplate.objects.all()
        card_components = models.CardComponent.objects.all()

        context = self.get_context_data(
            main_script='views/resource/report',
            report_templates=templates,
            templates_json=JSONSerializer().serialize(templates, sort_keys=False, exclude=['name', 'description']),
            card_components=card_components,
            card_components_json=JSONSerializer().serialize(card_components),
            cardwidgets=JSONSerializer().serialize(cardwidgets),
            tiles=JSONSerializer().serialize(permitted_tiles, sort_keys=False),
            cards=JSONSerializer().serialize(permitted_cards, sort_keys=False, exclude=[
                'is_editable', 'description', 'instructions', 'helpenabled', 'helptext', 'helptitle', 'ontologyproperty']),
            datatypes_json=JSONSerializer().serialize(
                datatypes, exclude=['modulename', 'issearchable', 'configcomponent', 'configname', 'iconclass']),
            geocoding_providers=geocoding_providers,
            inline_data=JSONSerializer().serialize(inlines, sort_keys=False),
            widgets=widgets,
            map_layers=map_layers,
            map_markers=map_markers,
            map_sources=map_sources,
            graph_id=graph.graphid,
            graph_name=graph.name,
            graph_json=JSONSerializer().serialize(graph, sort_keys=False, exclude=[
                'functions', 'relatable_resource_model_ids', 'domain_connections', 'edges', 'is_editable', 'description', 'iconclass', 'subtitle', 'author']),
            resourceid=resourceid,
            displayname=displayname,
        )

        if graph.iconclass:
            context['nav']['icon'] = graph.iconclass
        context['nav']['title'] = graph.name
        context['nav']['res_edit'] = True
        context['nav']['print'] = True
        context['nav']['print'] = True

        return render(request, 'views/resource/report.htm', context)
