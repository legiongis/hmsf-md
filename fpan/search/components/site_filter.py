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

from fpan.utils.permission_backend import (
    user_is_anonymous,
    user_is_scout,
    user_is_new_landmanager,
    user_is_old_landmanager,
)

logger = logging.getLogger(__name__)

details = {
    "searchcomponentid": "",
    "name": "Site Filter",
    "icon": "fa fa-key",
    "modulename": "site_filter.py",
    "classname": "SiteFilter",
    "type": "popup",
    "componentpath": "views/components/search/site-filter",
    "componentname": "site-filter",
    "sortorder": "0",
    "enabled": True,
}


def generate_no_access_filter(graph_name):
    graphid = str(GraphModel.objects.get(name=graph_name).pk)
    return {
        "access_level": "no_access",
        "filter_config": {
            "graphid": graphid,
        }
    }

def generate_full_access_filter(graph_name):
    graphid = str(GraphModel.objects.get(name=graph_name).pk)
    return {
        "access_level": "full_access",
        "filter_config": {
            "graphid": graphid,
        }
    }

def generate_attribute_filter(graph_name="", node_name="", value=[]):

    nodegroup_id = None
    if node_name and graph_name:
        node = Node.objects.filter(
            graph__name=graph_name,
            name=node_name,
        )
        if len(node) == 1:
            nodegroup_id = str(node[0].nodegroup_id)
        else:
            logger.warning(f"Attribute Filter: error finding single node '{node_name}' in {graph_name}.")
            return generate_no_access_filter(graph_name)

    if not isinstance(value, list):
        value = [value]

    return {
        "access_level": "attribute_filter",
        "filter_config": {
            "node_name": node_name,
            "nodegroup_id": nodegroup_id,
            "value": value
        }
    }

def generate_resourceid_filter(resourceids=[]):
    return {
        "access_level": "resourceid_filter",
        "filter_config": {
            "resourceids": resourceids
        }
    }

def generate_geo_filter(geometry=None):
    """Not implemented anywhere and will likely need more inputs, like a
    graphid"""
    return {
        "access_level": "geo_filter",
        "filter_config": {
            "geometry": geometry
        }
    }


class SiteFilter(BaseSearchFilter):

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
            self.apply_graph_filter(rule)

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
                rule = generate_full_access_filter(graph_name)

            elif user_is_new_landmanager(user):
                rule = user.landmanager.get_graph_filter(graph_name)

            elif user_is_old_landmanager(user):
                ## must retain old logic here until original land manager
                ## system is fully deprecated.
                logger.warning(f"old land manager: {user.username}")
                rule = self.get_rules(user, graphid)

            elif user_is_scout(user):
                rule = user.scout.scoutprofile.get_graph_filter(graph_name)

            elif user_is_anonymous(user):
                ## manual handling of public users here
                if graph_name == "Archaeological Site":
                    rule = generate_attribute_filter(
                        graph_name=graph_name,
                        node_name="Assigned To",
                        value=[user.username],
                    )

                elif graph_name == "Scout Report":
                    rule = generate_no_access_filter(graph_name)

                else:
                    rule = generate_full_access_filter(graph_name)

            else:
                rule = generate_no_access_filter(graph_name)

            compiled_rules.append(rule)

        if len(compiled_rules) == 1 and single is True:
            return compiled_rules[0]
        else:
            return compiled_rules

    def apply_graph_filter(self, rule):

        if rule["access_level"] == "full_access":
            self.apply_full_access_clause(rule["filter_config"]["graphid"])

        elif rule["access_level"] == "no_access":
            self.apply_no_access_clause(rule["filter_config"]["graphid"])

        elif rule["access_level"] == "attribute_filter":
            self.add_attribute_filter_clause(rule["filter_config"])

        elif rule["access_level"] == "geo_filter":
            self.add_geo_filter_clause(rule["filter_config"]["geometry"])

        elif rule["access_level"] == "resourceid_filter":
            self.add_resourceid_filter_clause(rule["filter_config"]["resourceids"])

        else:
            raise(Exception("Invalid rules for filter."))

    def apply_full_access_clause(self, graphid):
        self.paramount.should(Terms(field="graph_id", terms=graphid))

    def apply_no_access_clause(self, graphid):
        self.paramount.must_not(Terms(field="graph_id", terms=graphid))

    def add_geo_filter_clause(self, geometry):

        nested = self.create_nested_geo_filter(geometry)
        self.apply_nested_clause(nested)

    def add_attribute_filter_clause(self, filter_config):

        if "value_list" not in filter_config:
            if isinstance(filter_config["value"], list):
                filter_config["value_list"] = filter_config["value"]
            else:
                filter_config["value_list"] = filter_config["value"]

        nested = self.create_nested_attribute_filter(
            filter_config["nodegroup_id"],
            filter_config["value_list"],
        )
        self.apply_nested_clause(nested)

    def add_resourceid_filter_clause(self, resourceids):
        """incomplete at this time, but would pull a list of resource ids
        from somewhere and put it in the query."""

        new_resid_filter = Bool()
        new_resid_filter.should(Terms(field='resourceinstanceid', terms=resourceids))
        self.apply_nested_clause(new_resid_filter)

    def apply_nested_clause(self, clause):
        """
        This conditional handles situations where a new nested clause must
        honor an existing query without overwriting or ignoring it.
        """
        if self.existing_query:
            self.paramount.should(clause)
        else:
            self.paramount.must(clause)

    def get_rules(self, user, doc_id):

        full_access = {"access_level": "full_access"}
        no_access = {"access_level": "no_access"}
        attribute_filter = {
            "access_level": "attribute_filter",
            "filter_config": {
                "node_name": "",
                "value": ""
            }
        }
        geo_filter = {
            "access_level": "geo_filter",
            "filter_config": {
                "geometry": None
            }
        }

        settings_perms = settings.RESOURCE_MODEL_USER_RESTRICTIONS

        # assume full access if there is no condition in the settings.
        # also, don't apply any extra filters to superuser admins.
        if not doc_id in settings_perms or user.is_superuser:
            return full_access

        ## standard, basic check to apply restrictions to public users
        if user_is_anonymous(user):
            rules = copy.deepcopy(settings_perms[doc_id]['default'])

        else:
            rules = full_access

        ## alternative, FPAN-specific scenarios for Archaeological Sites
        if doc_id == "f212980f-d534-11e7-8ca8-94659cf754d0":
            if user_is_scout(user):
                rules = copy.deepcopy(settings_perms[doc_id]['default'])

            # special handling of the state land manager permissions here
            if user_is_old_landmanager(user):
                rules = self.get_state_node_match(user)

            elif user_is_new_landmanager(user):

                if user.landmanager.full_access is True:
                    rules = full_access

                elif user.landmanager.apply_area_filter is True:
                    ## this was supposed to be a proper geo_filter as below, but
                    ## that doesn't allow for arbitrary assignment of nearby
                    ## management areas.
                    # multipolygon = user.landmanager.areas_as_multipolygon
                    # geo_filter["filter_config"]["geometry"] = multipolygon
                    # rules = geo_filter

                    ## instead, apply attribute filter based on the names of
                    ## of associated areas.
                    attribute_filter["filter_config"]["node_name"] = "Management Area"
                    attribute_filter["filter_config"]["value"] = [i.name for i in user.landmanager.all_areas]
                    rules = attribute_filter

                elif user.landmanager.apply_agency_filter is True:
                    attribute_filter["filter_config"]["node_name"] = "Management Agency"
                    attribute_filter["filter_config"]["value"] = [user.landmanager.management_agency.name]
                    rules = attribute_filter

                else:
                    rules = no_access

            else:
                rules = no_access

        ## do a little bit of processing on attribute filters to standardize
        ## their configs 1) change node name to nodegroupids 2) handle <username>
        ## directive 3) set all values to lists for later iteration.
        if rules["access_level"] == "attribute_filter":

            node_name = rules["filter_config"]["node_name"]
            node = Node.objects.filter(
                graph_id=doc_id,
                name=node_name,
            )
            if len(node) == 1:
                ngid = str(node[0].nodegroup_id)
            else:
                logger.warning(f"Error finding node '{node_name}' in {doc_id}. Check rules-filter settings.")
                return no_access

            rules["filter_config"]["nodegroup_id"] = ngid

            if rules["filter_config"]["value"] == "<username>":
                if user.username == "anonymous":
                    rules["filter_config"]["value"] = ["anonymous"]
                else:
                    rules["filter_config"]["value"] = [user.username, "anonymous"]

            if isinstance(rules["filter_config"]["value"], list):
                rules["filter_config"]["value_list"] = rules["filter_config"]["value"]
            else:
                rules["filter_config"]["value_list"] = [rules["filter_config"]["value"]]

        return rules


    def get_state_node_match(self, user):
        """ this method still determines Land Manager access levels. but
        eventually it will be refactored to use the new LandManager model"""

        from fpan.models import ManagedArea

        full_access = {"access_level": "full_access"}
        no_access = {"access_level": "no_access"}
        attribute_filter = {
            "access_level": "attribute_filter",
            "filter_config": {
                "node_name": "",
                "value": ""
            }
        }

        # The FL_BAR user gets full access to all sites
        if user.groups.filter(name="FL_BAR").exists():
            return full_access

        # The FMSF user gets full access to all sites
        if user.groups.filter(name="FMSF").exists():
            return full_access

        elif user.groups.filter(name="StatePark").exists():

            # for the SPAdmin account, allow access to all sites in the state parks category
            if user.username == "SPAdmin":
                attribute_filter["filter_config"]["node_name"] = "Managed Area Category"
                attribute_filter["filter_config"]["value"] = "State Parks"
                return attribute_filter

            # for district users, return a list of all the park names in their district
            elif user.username.startswith("SPDistrict"):
                try:
                    dist_num = int(user.username[-1])
                except:
                    rules["access_level"] = "no_access"
                    return no_access

                parks = ManagedArea.objects.filter(sp_district=dist_num,
                    agency="FL Dept. of Environmental Protection, Div. of Recreation and Parks")

                attribute_filter["filter_config"]["node_name"] = "Managed Area Name"
                attribute_filter["filter_config"]["value"] = [p.name for p in parks]
                return attribute_filter

            # finally, normal state park users are only allowed to see those that match their username
            else:
                try:
                    park = ManagedArea.objects.get(nickname=user.username)
                except ManagedArea.DoesNotExist:
                    return no_access

                attribute_filter["filter_config"]["node_name"] = "Managed Area Name"
                attribute_filter["filter_config"]["value"] = park.name
                return attribute_filter

        # handle state forest access
        elif user.groups.filter(name="FL_Forestry").exists():

            # for the SFAdmin account, allow access to all sites in the state parks category
            if user.username == "SFAdmin":

                attribute_filter["filter_config"]["node_name"] = "Managed Area Category"
                attribute_filter["filter_config"]["value"] = "State Forest"
                return attribute_filter

            else:
                try:
                    forest = ManagedArea.objects.get(nickname=user.username)
                except:
                    return no_access

                attribute_filter["filter_config"]["node_name"] = "Managed Area Name"
                attribute_filter["filter_config"]["value"] = forest.name
                return attribute_filter

        elif user.groups.filter(name="FWC").exists():

            try:
                fwc = ManagedArea.objects.get(nickname=user.username)
            except:
                return no_access

            attribute_filter["filter_config"]["node_name"] = "Managed Area Name"
            attribute_filter["filter_config"]["value"] = fwc.name
            return attribute_filter

        elif user.groups.filter(name="FL_AquaticPreserve").exists():

            attribute_filter["filter_config"]["node_name"] = "Managing Agency"
            attribute_filter["filter_config"]["value"] = "FL Dept. of Environmental Protection, Florida Coastal Office"
            return attribute_filter

        elif user.groups.filter(name="FL_WMD").exists():

            if user.username == "SJRWMD_Admin":

                attribute_filter["filter_config"]["node_name"] = "Managed Area Category"
                attribute_filter["filter_config"]["value"] = "Water Management District"
                return attribute_filter

            elif user.username == "SJRWMD_NorthRegion":
                districts = ["North","North Central","West"]
                ma = ManagedArea.objects.filter(wmd_district__in=districts)

            elif user.username == "SJRWMD_SouthRegion":
                districts = ["South", "South Central", "Southwest"]
                ma = ManagedArea.objects.filter(wmd_district__in=districts)

            else:
                districts = ["North", "North Central", "West", "South", "Southwest", "South Central"]
                for district in districts:
                    if user.username.startswith("SJRWMD") and district.replace(" ","") in user.username:
                        ma = ManagedArea.objects.filter(wmd_district=district)

            attribute_filter["filter_config"]["node_name"] = "Managed Area Name"
            attribute_filter["filter_config"]["value"] = [m.name for m in ma]
            return attribute_filter

        else:
            return no_access

    def create_nested_attribute_filter(self, nodegroup_id, value_list):

        new_string_filter = Bool()
        new_string_filter.filter(Terms(field='strings.nodegroup_id', terms=[nodegroup_id]))
        for value in value_list:
            new_string_filter.should(Match(field='strings.string', query=value, type='phrase'))
        nested = Nested(path='strings', query=new_string_filter)
        return nested

    def create_nested_geo_filter(self, geometry):

        ## process GEOS geometry object into geojson and create ES filter
        geojson_geom = JSONDeserializer().deserialize(geometry.geojson)
        geoshape = GeoShape(
            field="geometries.geom.features.geometry",
            type=geojson_geom["type"],
            coordinates=geojson_geom["coordinates"]
        )

        new_spatial_filter = Bool()
        new_spatial_filter.filter(geoshape)
        nested = Nested(path='geometries', query=new_spatial_filter)
        return nested

    def quick_query(self, rules, doc):

        if rules["access_level"] == "attribute_filter":
            self.add_attribute_filter_clause(rules["filter_config"])

        elif rules["access_level"] == "geo_filter":
            self.add_geo_filter_clause(doc, rules["filter_config"]["geometry"])

        se = SearchEngineFactory().create()
        query = Query(se, start=0, limit=10000)
        query.include('graph_id')
        query.include('resourceinstanceid')
        query.add_query(self.paramount)

        ## doc_type is deprecated, must use a filter for graphid instead (i think)
        results = query.search(index='resources', doc_type=doc)

        return results

    def get_resource_access_from_es_query(self, user, graphid, invert=False):
        """
        Returns the resourceinstanceids for all resources that a user is allowed to
        access from a given graph. Set invert=True to return
        ids that the user is NOT allowed to access.
        """

        self.paramount = Bool()
        self.existing_query = False

        response = {
            "access_level": "partial_access",
            "id_list": []
        }

        rules = self.compile_rules(user, graphids=[graphid], single=True)

        if rules["access_level"] == "full_access":
            response["access_level"] = "full_access"
            return response

        if rules["access_level"] == "no_access":
            response["access_level"] = "no_access"
            return response

        try:
            if rules["access_level"] == "attribute_filter":
                self.add_attribute_filter_clause(rules["filter_config"])

            elif rules["access_level"] == "geo_filter":
                self.add_geo_filter_clause(rules["filter_config"]["geometry"])

            se = SearchEngineFactory().create()
            query = Query(se, start=0, limit=10000)
            query.include('graph_id')
            query.include('resourceinstanceid')
            query.add_query(self.paramount)

            ## doc_type is deprecated, must use a filter for graphid instead (i think)
            results = query.search(index='resources', doc_type=graphid)

        except Exception as e:
            print(e)
            results = self.quick_query(rules, graphid)

        resourceids = list(set([i['_source']['resourceinstanceid'] for i in results['hits']['hits']]))

        if invert is True:
            inverted_res = ResourceInstance.objects.filter(graph_id=graphid).exclude(resourceinstanceid__in=resourceids)
            resourceids = [str(i.resourceinstanceid) for i in inverted_res]

        response["id_list"] = resourceids

        return response

    def get_resource_list_from_es_query(self, rule, ids_only=False):
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

        if rule["access_level"] in ["full_access", "no_access"]:
            return list()

        self.apply_graph_filter(rule)

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
