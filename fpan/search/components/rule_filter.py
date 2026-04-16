import os
import json
import logging
from typing import TYPE_CHECKING
from arches.app.utils.betterJSONSerializer import JSONDeserializer, JSONSerializer
from arches.app.search.search_engine_factory import SearchEngineFactory
from arches.app.search.elasticsearch_dsl_builder import (
    Bool,
    Terms,
    GeoShape,
    Nested,
    Match,
    Query,
)
from arches.app.search.components.base import BaseSearchFilter
from arches.app.models.system_settings import settings
from arches.app.models.models import GraphModel, Node


logger = logging.getLogger(__name__)

details = {
    "searchcomponentid": "ade4886d-1111-4cd5-ac30-5b1eb6e3bef3",
    "name": "Rule Filter",
    "icon": "fa fa-key",
    "modulename": "rule_filter.py",
    "classname": "RuleFilter",
    "type": "popup",
    "componentpath": "views/components/search/rule-filter",
    "componentname": "rule-filter",
    "sortorder": "0",
    "config": {},
}


class Rule(object):
    def __init__(self, rule_type: str, **kwargs):

        self.type = rule_type
        self.graph_id = kwargs.get("graph_id")
        self.config = {}

        if self.type in ["full_access", "no_access"]:
            self.config["graph_id"] = self.graph_id

        elif self.type == "attribute_filter":
            node_id = kwargs.get("node_id")
            if not node_id or not self.graph_id:
                raise (Exception(f"Invalid params for {self.type} rule."))

            try:
                node = Node.objects.get(pk=node_id)
            except Node.DoesNotExist:
                raise (Exception(f"rule error: Can't find single node '{node_id}'"))

            value = kwargs.get("value", [])
            if not isinstance(value, list):
                value = [value]

            self.config["node_name"] = node.name
            if node.nodegroup is None:
                raise (Exception(f"node error: No nodegroup on this node '{node_id}'"))
            self.config["nodegroup_id"] = str(node.nodegroup.pk)
            self.config["value"] = value

        elif self.type == "resourceid_filter":
            self.config["resourceids"] = kwargs.get("resourceids", [])

        elif self.type == "geo_filter":
            self.config["geometry"] = kwargs.get("geometry")

        else:
            raise (Exception(f"Invalid rule type: {self.type}"))

    def serialize(self):

        return {
            "type": self.type,
            "config": self.config,
        }


class RuleFilter(BaseSearchFilter):
    def append_dsl(self, search_query_object, **kwargs):
        """
        This is the method that Arches calls, and ultimately all it does is

          search_query_object["query"].add_query(some_new_es_dsl)

        Many other methods of this class are used as helpers for generating
        the new dsl content, which is stored in self.paramount.
        """

        if TYPE_CHECKING and not self.request:
            return

        ## set some properties here, as this is the access method Arches uses
        ## to instantiate this class.
        self.paramount = Bool()
        self.existing_query = False

        ## manual test to see if any criteria have been added to the query yet
        original_dsl = search_query_object["query"]._dsl
        try:
            if original_dsl["query"]["match_all"] == {}:
                self.existing_query = True
        except KeyError:
            pass

        if settings.LOG_LEVEL == "DEBUG":
            with open(os.path.join(settings.LOG_DIR, "dsl_before_fpan.json"), "w") as o:
                json.dump(
                    json.loads(JSONSerializer().serialize(original_dsl)),
                    o,
                    indent=1,
                )

        ## Should always be enabled. If not (like someone typed in a different URL) raise exception.
        querystring_params = self.request.GET.get(details["componentname"])
        if querystring_params != "enabled":
            raise (
                Exception("Error: Site filter is registered but not shown as enabled.")
            )

        ## first list all graph ids so rules will be made for each one
        graphids_uuid = (
            GraphModel.objects.exclude(pk=settings.SYSTEM_SETTINGS_RESOURCE_MODEL_ID)
            .exclude(isresource=False)
            .exclude(publication=None)
            .values_list("graphid", flat=True)
        )
        graphids = [str(i) for i in graphids_uuid]

        ## then honor the resource-type-filter if it exists
        type_filter = self.request.GET.get("resource-type-filter")
        if type_filter:
            deserialized_type_filter = JSONDeserializer().deserialize(type_filter)
            if (
                deserialized_type_filter
                and isinstance(deserialized_type_filter, list)
                and len(deserialized_type_filter) > 0
            ):
                type_filter_params = deserialized_type_filter[0]
                if type_filter_params["inverted"] is True:
                    graphids.remove(type_filter_params["graphid"])
                else:
                    graphids = [type_filter_params["graphid"]]
            else:
                logger.warning(
                    f"unexpected resource-type-filter content: {deserialized_type_filter}"
                )

        ## now create a user-determined rule for each graph in the request.
        ## collected rules are created with the rule generators above.
        from hms.permissions_backend import get_rule_by_graph

        collected_rules = [
            get_rule_by_graph(self.request.user, graphid=i) for i in graphids
        ]

        ## iterate rules, applying them to self.paramount thereby generating
        ## a composite query.
        for rule in collected_rules:
            self.apply_rule(rule)

        search_query_object["query"].add_query(self.paramount)

        if settings.LOG_LEVEL == "DEBUG":
            with open(os.path.join(settings.LOG_DIR, "dsl_after_fpan.json"), "w") as o:
                json.dump(
                    json.loads(
                        JSONSerializer().serialize(search_query_object["query"]._dsl)
                    ),
                    o,
                    indent=1,
                )

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
            raise (Exception("Invalid rules for filter."))

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
        terms = Terms(field="strings.nodegroup_id", terms=[rule_config["nodegroup_id"]])
        attribute_bool.filter(terms)
        for value in rule_config["value"]:
            match = Match(field="strings.string", query=value, type="phrase")
            attribute_bool.should(match)

        nested = Nested(path="strings", query=attribute_bool)

        if self.existing_query:
            self.paramount.should(nested)
        else:
            self.paramount.must(nested)

    def add_resourceid_filter_clause(self, resourceids):
        """incomplete at this time, but would pull a list of resource ids
        from somewhere and put it in the query."""

        resid_bool = Bool()
        terms = Terms(field="resourceinstanceid", terms=resourceids)
        resid_bool.should(terms)

        if self.existing_query:
            self.paramount.should(resid_bool)
        else:
            self.paramount.must(resid_bool)

    def add_geo_filter_clause(self, geometry):

        geojson_geom = JSONDeserializer().deserialize(geometry.geojson)
        geoshape = None
        if isinstance(geojson_geom, dict):
            geom_type = geojson_geom.get("type")
            geom_coords = geojson_geom.get("coordinates")
            if geom_type and geom_coords:
                geoshape = GeoShape(
                    field="geometries.geom.features.geometry",
                    type=geojson_geom["type"],
                    coordinates=geojson_geom["coordinates"],
                )

        if geoshape:
            spatial_bool = Bool()
            spatial_bool.filter(geoshape)
            nested = Nested(path="geometries", query=spatial_bool)

            if self.existing_query:
                self.paramount.should(nested)
            else:
                self.paramount.must(nested)

        else:
            logger.warning(f"error constructing geoshape from geojson: {geojson_geom}")

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
        query.include("graph_id")
        query.include("resourceinstanceid")
        query.include("displayname")
        query.add_query(self.paramount)

        results = query.search(index="resources")

        if ids_only is True:
            return [i["_source"]["resourceinstanceid"] for i in results["hits"]["hits"]]

        return [i["_source"] for i in results["hits"]["hits"]]
