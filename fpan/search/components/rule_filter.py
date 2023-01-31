import os
import json
import copy
import logging
from arches.app.utils.betterJSONSerializer import JSONDeserializer
from arches.app.search.search_engine_factory import SearchEngineFactory
from arches.app.search.elasticsearch_dsl_builder import Bool, Terms, GeoShape, Nested, Match, Query
from arches.app.search.components.base import BaseSearchFilter
from arches.app.models.system_settings import settings
from arches.app.models.models import GraphModel, Node, ResourceInstance
from arches.app.utils.betterJSONSerializer import JSONSerializer, JSONDeserializer

from hms.permissions_backend import (
    user_is_anonymous,
    user_is_scout,
    user_is_land_manager,
)

logger = logging.getLogger(__name__)

details = {
    "searchcomponentid": "",
    "name": "Rule Filter",
    "icon": "fa fa-key",
    "modulename": "rule_filter.py",
    "classname": "RuleFilter",
    "type": "popup",
    "componentpath": "views/components/search/rule-filter",
    "componentname": "rule-filter",
    "sortorder": "0",
    "enabled": True,
}

class Rule(object):

    def __init__(self, rule_type, **kwargs):

        self.type = rule_type
        self.graph_id = kwargs.get("graph_id")
        self.graph_name = kwargs.get("graph_name")
        self.config = {}

        if not self.graph_id and self.graph_name:
            self.graph_id = str(GraphModel.objects.get(name=self.graph_name).pk)

        if self.type in ["full_access", "no_access"]:
            self.config["graph_id"] = self.graph_id

        elif self.type == "attribute_filter":
            node_name = kwargs.get("node_name")
            if not node_name or not self.graph_id:
                raise(Exception(f"Invalid params for {self.type} rule."))

            node = Node.objects.filter(graph=self.graph_id, name=node_name)
            if len(node) == 1:
                nodegroup_id = str(node[0].nodegroup_id)
            else:
                raise(Exception(f"rule error: Can't find single node '{node_name}' in {self.graph_name}."))

            value = kwargs.get("value", [])
            if not isinstance(value, list):
                value = [value]

            self.config["node_name"] = node_name
            self.config["nodegroup_id"] = nodegroup_id
            self.config["value"] = value

        elif self.type == "resourceid_filter":
            self.config["resourceids"] = kwargs.get("resourceids", [])

        elif self.type == "geo_filter":
            self.config["geometry"] = kwargs.get("geometry")

        else:
            raise(Exception(f"Invalid rule type: {self.type}"))

    def serialize(self):

        return {
            "type": self.type,
            "config": self.config,
        }



class RuleFilter(BaseSearchFilter):

    def append_dsl(self, search_results_object, permitted_nodegroups, include_provisional):
        """
        This is the method that Arches calls, and ultimately all it does is

          search_results_object["query"].add_query(some_new_es_dsl)
        
        Many other methods of this class are used as helpers for generating
        the new dsl content, which is stored in self.paramount.
        """

        ## set some properties here, as this is the access method Arches uses
        ## to instantiate this class.
        self.paramount = Bool()
        self.existing_query = False

        ## manual test to see if any criteria have been added to the query yet
        original_dsl = search_results_object["query"]._dsl
        try:
            if original_dsl['query']['match_all'] == {}:
                self.existing_query = True
        except KeyError:
            pass

        if settings.LOG_LEVEL == "DEBUG":
            with open(os.path.join(settings.LOG_DIR, "dsl_before_fpan.json"), "w") as output:
                json.dump(original_dsl, output, indent=1)

        ## Should always be enabled. If not (like someone typed in a different URL) raise exception.
        querystring_params = self.request.GET.get(details["componentname"])
        if querystring_params != "enabled":
            raise(Exception("Error: Site filter is registered but not shown as enabled."))

        ## first list all graph ids so rules will be made for each one
        graphids_uuid = (
            GraphModel.objects.exclude(pk=settings.SYSTEM_SETTINGS_RESOURCE_MODEL_ID)
            .exclude(isresource=False)
            .exclude(isactive=False).values_list('graphid', flat=True)
        )
        graphids = [str(i) for i in graphids_uuid]

        ## then honor the resource-type-filter if it exists
        type_filter = self.request.GET.get("resource-type-filter")
        if type_filter:
            type_filter_params = JSONDeserializer().deserialize(type_filter)[0]
            if type_filter_params["inverted"] is True:
                graphids.remove(type_filter_params["graphid"])
            else:
                graphids = [type_filter_params["graphid"]]

        ## now create a user-determined rule for each graph in the request.
        ## collected rules are created with the rule generators above.
        collected_rules = self.compile_rules(self.request.user, graphids=graphids)

        ## iterate rules, applying them to self.paramount thereby generating
        ## a composite query.
        for rule in collected_rules:
            self.apply_rule(rule)

        search_results_object["query"].add_query(self.paramount)

        if settings.LOG_LEVEL == "DEBUG":
            with open(os.path.join(settings.LOG_DIR, "dsl_after_fpan.json"), "w") as output:
                json.dump(search_results_object["query"]._dsl, output, indent=1)
    
    def compile_rules(self, user, graphids=[], single=False):
        """
        Pass in a user and a list of graphids to generate filters for each graph
        based on user characteristics. If a single graphid is passed in, then
        you can add single=True to return a single rule, instead of a list
        containing only one rule.

        Potentially, user-defined settings could be pulled in here to extrapolate
        this logic to the front-end.
        """

        compiled_rules = []
        for graphid in graphids:
            graph_name = GraphModel.objects.get(graphid=graphid).name

            if user.is_superuser:
                rule = Rule("full_access", graph_name=graph_name)

            elif user_is_land_manager(user):
                rule = user.landmanager.get_graph_rule(graph_name)

            elif user_is_scout(user):
                rule = user.scout.scoutprofile.get_graph_rule(graph_name)

            elif user_is_anonymous(user):
                ## manual handling of public users here
                if graph_name == "Archaeological Site":
                    rule = Rule("attribute_filter",
                        graph_name=graph_name,
                        node_name="Assigned To",
                        value=[user.username],
                    )

                elif graph_name == "Scout Report":
                    from hms.models import report_rule_from_arch_rule
                    arch_rule = Rule("attribute_filter",
                        graph_name="Archaeological Site",
                        node_name="Assigned To",
                        value=[user.username],
                    )
                    rule = report_rule_from_arch_rule(arch_rule)

                else:
                    rule = Rule("full_access", graph_name=graph_name)

            else:
                # this will catch old land managers before their profiles
                # have been created.
                logger.debug(f"compile_rules: user {user.username} is adrift.")
                if graph_name in ["Archaeological Site", "Scout Report"]:
                    rule = Rule("no_access", graph_name=graph_name)
                else:
                    rule = Rule("full_access", graph_name=graph_name)

            compiled_rules.append(rule)

        if len(compiled_rules) == 1 and single is True:
            return compiled_rules[0]
        else:
            return compiled_rules

    def apply_rule(self, rule):

        if rule.type == "full_access":
            self.add_full_access_clause(rule.config["graph_id"])

        elif rule.type == "no_access":
            self.add_no_access_clause(rule.config["graph_id"])

        elif rule.type == "attribute_filter":
            self.add_attribute_filter_clause(rule.config)

        elif rule.type == "geo_filter":
            self.add_geo_filter_clause(rule.config["geometry"])

        elif rule.type == "resourceid_filter":
            self.add_resourceid_filter_clause(rule.config["resourceids"])

        else:
            raise(Exception("Invalid rules for filter."))

    def add_full_access_clause(self, graphid):

        terms = Terms(
            field="graph_id",
            terms=graphid,
        )

        self.paramount.should(terms)

    def add_no_access_clause(self, graphid):

        terms = Terms(
            field="graph_id",
            terms=graphid,
        )

        self.paramount.must_not(terms)

    def add_attribute_filter_clause(self, rule_config):

        attribute_bool = Bool()
        terms = Terms(
            field='strings.nodegroup_id',
            terms=[rule_config["nodegroup_id"]]
        )
        attribute_bool.filter(terms)
        for value in rule_config["value"]:
            match = Match(
                field='strings.string',
                query=value,
                type='phrase'
            )
            attribute_bool.should(match)

        nested = Nested(
            path='strings',
            query=attribute_bool
        )

        if self.existing_query:
            self.paramount.should(nested)
        else:
            self.paramount.must(nested)

    def add_resourceid_filter_clause(self, resourceids):
        """incomplete at this time, but would pull a list of resource ids
        from somewhere and put it in the query."""

        resid_bool = Bool()
        terms = Terms(
            field='resourceinstanceid',
            terms=resourceids
        )
        resid_bool.should(terms)

        if self.existing_query:
            self.paramount.should(resid_bool)
        else:
            self.paramount.must(resid_bool)

    def add_geo_filter_clause(self, geometry):

        geojson_geom = JSONDeserializer().deserialize(geometry.geojson)
        geoshape = GeoShape(
            field="geometries.geom.features.geometry",
            type=geojson_geom["type"],
            coordinates=geojson_geom["coordinates"]
        )

        spatial_bool = Bool()
        spatial_bool.filter(geoshape)
        nested = Nested(
            path='geometries',
            query=spatial_bool
        )

        if self.existing_query:
            self.paramount.should(nested)
        else:
            self.paramount.must(nested)

    def get_resources_from_rule(self, rule, ids_only=False):
        """
        Returns a list of resources for single graph_filter rule. This
        can be used in other parts of the app, like MVT() or decorators.
        Note the 10000 item limit. If you are trying to get a list of resource
        ids larger than 10000 you may need to rethink this strategy.

        Use ids_only=True to get a flat list of ids, otherwise each item in
        the returned list is a small dictionary with 'resourceid', 'graph_id'
        and 'displayname'. 
        """

        self.paramount = Bool()
        self.existing_query = False

        if rule.type in ["full_access", "no_access"]:
            return list()

        self.apply_rule(rule)

        se = SearchEngineFactory().create()
        query = Query(se, start=0, limit=10000)
        query.include('graph_id')
        query.include('resourceinstanceid')
        query.include('displayname')
        query.add_query(self.paramount)

        results = query.search(index='resources')

        if ids_only is True:
            ids = [i['_source']['resourceinstanceid'] for i in results['hits']['hits']]
            return ids

        return [i['_source'] for i in results['hits']['hits']]
