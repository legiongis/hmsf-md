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


def generate_no_access_filter():
    return {"access_level": "no_access"}

def generate_full_access_filter():
    return {"access_level": "full_access"}

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
            logger.warning(f"Error finding single node '{node_name}' in {graph_name}.")
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

def generate_geo_filter(geometry=None):
    return {
        "access_level": "geo_filter",
        "filter_config": {
            "geometry": geometry
        }
    }


class SiteFilter(BaseSearchFilter):

    def append_dsl(self, search_results_object, permitted_nodegroups, include_provisional):

        ## set some class properties here, as this is the access method Arches uses
        ## to instantiate this object.
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

        querystring_params = self.request.GET.get(details["componentname"], "")

        ## Should always be enabled. If not (like someone typed in a different URL) raise exception.
        if querystring_params != "enabled":
            raise(Exception("Site filter is registered but not shown as enabled."))

        try:

            collected_rules = self.compile_rules(self.request.user, graphlist=self.get_doc_types())

            ## iterate rules and generate a composite query based on them
            for graphid, rule in collected_rules.items():

                if rule["access_level"] == "full_access":
                    self.add_full_access_clause(graphid)

                elif rule["access_level"] == "no_access":
                    self.add_no_access_clause(graphid)

                elif rule["access_level"] == "attribute_filter":
                    self.add_attribute_filter_clause(graphid, rule["filter_config"])

                elif rule["access_level"] == "geo_filter":
                    self.add_geo_filter_clause(graphid, rule["filter_config"]["geometry"])

                else:
                    raise(Exception("Invalid rules for filter."))

                # else:
                    # make called to access table and if under 1500 resources are
                    # allowed, then push all of these resource ids directly to
                    # the ES query. Otherwise, revert to using the actual
                    # query rules.

                    #allowed = UserXResourceInstanceAccess.objects.filter(
                    #    user=self.request.user,
                    #    resource__graph_id=graphid,
                    #)
                    # if len(allowed) < 1500:
                    #     # this should be altered to take the resids as an arg 
                    #     self.add_resourceid_filter_clause(graphid, self.request.user)
                    #else:
                        # if rule["access_level"] == "geo_filter":
                        #     self.add_geo_filter_clause(graphid, rule["filter_config"]["geometry"])
                        #     # self.create_geo_filter(graphid, rules["filter_config"]["geometry"])
                        #
                        # elif rule["access_level"] == "attribute_filter":
                        #     # self.create_attribute_filter(graphid, rule["filter_config"])
                        #     self.add_attribute_filter_clause(graphid, rule["filter_config"])
                        # else:
                            # raise(Exception("Invalid rules for filter."))

                    # if hasattr(self.request.user, 'landmanager'):
                    #     self.add_resourceid_filter_clause(graphid, self.request.user)

                    # else:
                    #     if rule["access_level"] == "geo_filter":
                    #         self.add_geo_filter_clause(graphid, rule["filter_config"]["geometry"])
                    #         # self.create_geo_filter(graphid, rules["filter_config"]["geometry"])

                    #     else:
                    #         raise(Exception("Invalid rules for filter."))

            search_results_object["query"].add_query(self.paramount)

            if settings.LOG_LEVEL == "DEBUG":
                with open(os.path.join(settings.LOG_DIR, "dsl_after_fpan.json"), "w") as output:
                    json.dump(search_results_object["query"]._dsl, output, indent=1)

        except Exception as e:
            print("\n\n")
            print(e)
            logger.debug(e)
            raise(e)
    
    def compile_rules(self, user, graph=None, graphlist=[]):

        ## handle input of single graphid or multiple graphids
        if graph is not None:
            graphids = [graph]
        elif len(graphlist) > 0:
            graphids = graphlist
        else:
            return {}

        compiled_rules = {}
        for graphid in graphids:
            graph_name = GraphModel.objects.get(graphid=graphid).name

            if user.is_superuser:
                compiled_rules[graphid] = generate_full_access_filter()
                continue

            elif user_is_new_landmanager(user):
                logger.debug(f"new land manager: {user.username}")
                rule = user.landmanager.site_access_rules.get(graph_name)
                if rule is None:
                    rule = generate_full_access_filter()
                compiled_rules[graphid] = rule

            elif user_is_old_landmanager(user):
                ## must retain old logic here until original land manager
                ## system is fully deprecated.
                logger.debug(f"old land manager: {user.username}")
                compiled_rules[graphid] = self.get_rules(user, graphid)

            elif user_is_scout(user):
                rule = user.scout.scoutprofile.site_access_rules.get(graph_name)
                if rule is None:
                    rule = generate_full_access_filter()
                compiled_rules[graphid] = rule

            elif user_is_anonymous(user):
                ## manual handling of public users here
                if graph_name == "Archaeological Site":
                    compiled_rules[graphid] = generate_attribute_filter(
                        graph_name=graph_name,
                        node_name="Assigned To",
                        value=[user.username],
                    )

                elif graph_name == "Scout Report":
                    compiled_rules[graphid] = generate_no_access_filter()

                else:
                    compiled_rules[graphid] = generate_full_access_filter()

            else:
                compiled_rules[graphid] = generate_no_access_filter()

        ## return single ruleset if graph was provided, full dict
        ## if graphlist was provided
        if graph is not None:
            return compiled_rules[graph]
        else:
            return compiled_rules

    def add_full_access_clause(self, graphid):
        self.paramount.should(Terms(field="graph_id", terms=graphid))

    def add_no_access_clause(self, graphid):
        self.paramount.must_not(Terms(field="graph_id", terms=graphid))

    def add_geo_filter_clause(self, graphid, geometry):

        nested = self.create_nested_geo_filter(geometry)
        if self.existing_query:
            self.paramount.should(nested)
        else:
            self.paramount.must(nested)

    def add_attribute_filter_clause(self, graphid, filter_config):

        if "value_list" not in filter_config:
            if isinstance(filter_config["value"], list):
                filter_config["value_list"] = filter_config["value"]
            else:
                filter_config["value_list"] = filter_config["value"]

        nested = self.create_nested_attribute_filter(
            graphid,
            filter_config["nodegroup_id"],
            filter_config["value_list"],
        )
        if self.existing_query:
            self.paramount.should(nested)
        else:
            self.paramount.must(nested)


    def add_resourceid_filter_clause(self, graphid, user):
        """incomplete at this time, but would pull a list of resource ids
        from somewhere and put it in the query."""

        # resids = [str(i.resource.resourceinstanceid) for i in allowed]

        # new_resid_filter = Bool()
        # new_resid_filter.should(Terms(field='resourceinstanceid', terms=resids))
        # if self.existing_query:
        #     self.paramount.should(new_resid_filter)
        # else:
        #     self.paramount.must(new_resid_filter)

        pass

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

    def get_doc_types(self, request=None):
        """ This is a more robust version of the analogous method in core Arches.
        It was moved here a long time ago, it's possible that current core Arches
        has been updated and this method could be removed to use that one."""

        if request is None:
            request = self.request

        all_resource_graphids = (
            GraphModel.objects.filter(isresource=True, isactive=True)
            .exclude(name="Arches System Settings")
        ).values_list('graphid', flat=True)

        type_filter = request.GET.get('typeFilter', '')
        use_ids = []

        if type_filter != '':
            type_filters = JSONDeserializer().deserialize(type_filter)

            ## add all positive filters to the list of good ids
            pos_filters = [i['graphid'] for i in type_filters if not i['inverted']]
            for pf in pos_filters:
                use_ids.append(pf)

            ## if there are negative filters, make a list of all possible ids and
            ## subtract the negative filter ids from it.
            neg_filters = [i['graphid'] for i in type_filters if i['inverted']]
            if len(neg_filters) > 0:
                use_ids = [str(i) for i in all_resource_graphids if not str(i) in neg_filters]

        else:
            use_ids = [str(i) for i in all_resource_graphids]

        if len(use_ids) == 0:
            ret = []
        else:
            ret = list(set(use_ids))
        return ret

    def create_nested_attribute_filter(self, doc_id, nodegroup_id, value_list):

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
            self.add_attribute_filter_clause(doc, rules["filter_config"])

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

        rules = self.compile_rules(user, graphid)

        if rules["access_level"] == "full_access":
            response["access_level"] = "full_access"
            return response

        if rules["access_level"] == "no_access":
            response["access_level"] = "no_access"
            return response

        try:
            if rules["access_level"] == "attribute_filter":
                self.add_attribute_filter_clause(graphid, rules["filter_config"])

            elif rules["access_level"] == "geo_filter":
                self.add_geo_filter_clause(graphid, rules["filter_config"]["geometry"])

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

    def get_resource_list_from_es_query(self, rules, graphid, invert=False, full_results=False):
        """
        Returns the resourceinstanceids for all resources for a given graph
        that match a set of rules. Set invert=True to return
        ids that do NOT match this query.
        """

        self.paramount = Bool()
        self.existing_query = False

        if rules["access_level"] in ["full_access", "no_access"]:
            return list()

        if rules["access_level"] == "attribute_filter":
            self.add_attribute_filter_clause(graphid, rules["filter_config"])

        elif rules["access_level"] == "geo_filter":
            self.add_geo_filter_clause(graphid, rules["filter_config"]["geometry"])

        se = SearchEngineFactory().create()
        query = Query(se, start=0, limit=10000)
        query.include('graph_id')
        query.include('resourceinstanceid')
        query.include('displayname')
        query.add_query(self.paramount)

        results = query.search(index='resources')

        if full_results is True:
            return [i['_source'] for i in results['hits']['hits']]

        resourceids = list(set([i['_source']['resourceinstanceid'] for i in results['hits']['hits']]))

        if invert is True:
            i_resids = ResourceInstance.objects.filter(
                graph_id=graphid
            ).exclude(resourceinstanceid__in=resourceids).values_list("resourceinstanceid", flat=True)
            resourceids = [str(i) for i in i_resids]

        return resourceids
