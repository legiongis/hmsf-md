import os
import json
import logging
from arches.app.utils.betterJSONSerializer import JSONDeserializer
from arches.app.search.search_engine_factory import SearchEngineFactory
from arches.app.search.elasticsearch_dsl_builder import Bool, Terms, GeoShape, Nested, Match, Query
from arches.app.search.components.base import BaseSearchFilter
from arches.app.models.system_settings import settings
from arches.app.models.models import GraphModel, Node
from arches.app.utils.betterJSONSerializer import JSONSerializer, JSONDeserializer

from fpan.utils.permission_backend import (
    user_is_anonymous,
    user_is_scout,
    user_is_land_manager,
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


class SiteFilter(BaseSearchFilter):
    def append_dsl(self, search_results_object, permitted_nodegroups, include_provisional):

        original_dsl = search_results_object["query"]._dsl
        if settings.LOG_LEVEL == "DEBUG":
            with open(os.path.join(settings.LOG_DIR, "dsl_before_fpan.json"), "w") as output:
                json.dump(original_dsl, output, indent=1)

        querystring_params = self.request.GET.get(details["componentname"], "")

        ## Should always be enabled. If not, raise exception.
        if querystring_params != "enabled":
            raise(Exception("Site filter is registered but not shown as enabled."))

        try:

            docs_perms = settings.RESOURCE_MODEL_USER_RESTRICTIONS
            doc_types = self.get_doc_types(self.request)

            clause = None
            print(doc_types)
            for doc in doc_types:

                print("getting perms for " + doc)

                rules = self.get_match_conditions(self.request.user, doc)
                print(rules)
                if rules == "full_access":
                    continue

                elif rules == "no_access":
                    clause = self.add_doc_specific_criterion(original_dsl, doc, doc_types, no_access=True)

                else:
                    clause = self.add_doc_specific_criterion(original_dsl, doc, doc_types, criterion=rules)

            # clause = self.make_management_area_geofilter(request.user, doc_type="f212980f-d534-11e7-8ca8-94659cf754d0")

            if not clause is None:
                search_results_object["query"].add_query(clause)

            # coords = [[[-81.477111876252,29.133006285427328],[-81.47314589490625,28.67123161923965],[-81.06663280694531,28.667751860292498],[-81.07258177896466,29.134738397156326],[-81.477111876252,29.133006285427328]]]
            # geoshape = GeoShape(
            #     field="geometries.geom.features.geometry", type="Polygon", coordinates=coords
            # )
            #
            # try:
            #     self.request.user.ManagerProfile
            # except Exception as e:
            #     print(e)
            #
            #
            # spatial_query = Bool()
            # spatial_query.filter(geoshape)
            #
            # search_query = Bool()
            # search_query.filter(Nested(path="geometries", query=spatial_query))
            #
            # search_results_object["query"].add_query(search_query)
            # print(search_results_object["query"])

            if settings.LOG_LEVEL == "DEBUG":
                with open(os.path.join(settings.LOG_DIR, "dsl_after_fpan.json"), "w") as output:
                    json.dump(search_results_object["query"]._dsl, output, indent=1)

        except Exception as e:
            print("\n\n")
            print(e)
            logger.debug(e)

    def get_match_conditions(self, user, graphid):

        print("get_match_conditions 2.0")

        graphid = str(graphid)

        # allow superuser admins to get full access to everything
        if user.is_superuser:
            return "full_access"

        docs_perms = settings.RESOURCE_MODEL_USER_RESTRICTIONS
        # assume full access if there is no condition in the settings.
        if graphid not in docs_perms:
            return "full_access"

        ## standard, basic check to apply restrictions to public users
        if user_is_anonymous(user):
            print("  anonymous user")
            perm_settings = docs_perms[graphid]['public']

        ## alternative, FPAN-specific scenarios
        elif user_is_scout(user):
            print("  scout user")
            perm_settings = docs_perms[graphid]['scout']

        # special handling of the state land manager permissions here
        elif user_is_land_manager(user):
            ## TEMPORARY extra check to see if this is a 1.0 or 2.0 land manager
            filter_config = "no_access"
            if hasattr(user, "landmanager"):
                state_user = True
                print("  land manager 2.0")
                filter_config = self.handle_land_manager(user)
            else:
                print("  land manager 1.0")
                filter_config = self.get_state_node_match(user)
            print("filter_config:")
            print(filter_config)
            return filter_config

        # now interpret the filter. if no access is granted it's very easy
        if perm_settings['access_level'] == "no_access":
            return "no_access"

        # if a node value match (resource instance filtering) is required, a bit more
        # logic is required to determine what that node value is
        elif perm_settings['access_level'] == "match_node_value":

            # create the filter config that will be returned
            filter_config = {
                "node_name": perm_settings['match_config']['node_name'],
                "value": None,
            }

            # now conditionally find the value that should be matched against using
            # the node named above. Add 'anonymous' to allow scouts to see public
            # access sites while they are logged in.
            if perm_settings['match_config']['match_to'] == "<username>":
                filter_config['value'] = [user.username, "anonymous"]

            # generic allowance for specific, non-user-derived values to be passed in
            else:
                filter_config['value'] = filter_config['match_config']['match_to']

        return filter_config

    def handle_land_manager(self, user):

        if user.landmanager.full_access is True:
            return "full_access"

        if user.landmanager.apply_area_filter is True:
            areas = user.landmanager.get_areas()
            print(areas)
        return "full_access"

    def get_state_node_match(self, user):

        from fpan.models import ManagedArea

        # The FL_BAR user gets full access to all sites
        if user.groups.filter(name="FL_BAR").exists():
            return "full_access"

        # The FMSF user gets full access to all sites
        if user.groups.filter(name="FMSF").exists():
            return "full_access"

        elif user.groups.filter(name="StatePark").exists():

            # for the SPAdmin account, allow access to all sites in the state parks category
            if user.username == "SPAdmin":
                return {
                    'node_name': "Managed Area Category",
                    'value': "State Parks"
                }

            # for district users, return a list of all the park names in their district
            elif user.username.startswith("SPDistrict"):
                try:
                    dist_num = int(user.username[-1])
                except:
                    return "no_access"

                parks = ManagedArea.objects.filter(sp_district=dist_num,
                    agency="FL Dept. of Environmental Protection, Div. of Recreation and Parks")

                return {
                    'node_name': "Managed Area Name",
                    'value': [p.name for p in parks]
                }

            # finally, normal state park users are only allowed to see those that match their username
            else:
                try:
                    park = ManagedArea.objects.get(nickname=user.username)
                except ManagedArea.DoesNotExist:
                    return "no_access"

                return {
                    'node_name': "Managed Area Name",
                    'value': park.name
                }

        # handle state forest access
        elif user.groups.filter(name="FL_Forestry").exists():

            # for the SFAdmin account, allow access to all sites in the state parks category
            if user.username == "SFAdmin":
                return {
                    'node_name': "Managed Area Category",
                    'value': "State Forest"
                }

            else:
                try:
                    forest = ManagedArea.objects.get(nickname=user.username)
                except:
                    return "no_access"

                return {
                    'node_name': "Managed Area Name",
                    'value': forest.name
                }

        elif user.groups.filter(name="FWC").exists():

            try:
                fwc = ManagedArea.objects.get(nickname=user.username)
            except:
                return "no_access"

            return {
                'node_name': "Managed Area Name",
                'value': fwc.name
            }

        elif user.groups.filter(name="FL_AquaticPreserve").exists():

            return {
                'node_name': "Managing Agency",
                'value': "FL Dept. of Environmental Protection, Florida Coastal Office"
            }

        elif user.groups.filter(name="FL_WMD").exists():

            if user.username == "SJRWMD_Admin":
                return {
                    'node_name': "Managed Area Category",
                    'value': "Water Management District"
                }

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

            return {
                'node_name': "Managed Area Name",
                'value': [m.name for m in ma]
            }

        else:
            return "no_access"

    def get_doc_types(self, request):

        all_resource_graphids = (
            GraphModel.objects.exclude(pk=settings.SYSTEM_SETTINGS_RESOURCE_MODEL_ID)
            .exclude(isresource=False)
            .exclude(isactive=False)
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

    def add_doc_specific_criterion(self, original_dsl, spec_type, all_types, no_access=False, criterion=False):

        logger.debug("adding criterion: {} to {}".format(criterion, spec_type))

        try:
            paramount = Bool()

            for doc_type in all_types:

                ## add special string filter for specified node in type
                if doc_type == spec_type:

                    ## if no_access is the permission level for the user, exclude doc
                    if no_access is True:
                        logger.debug("restricting access to {}".format(doc_type))
                        paramount.must_not(Terms(field="graph_id", terms=doc_type))
                        continue

                    elif criterion is not False:
                        node = Node.objects.filter(graph_id=spec_type,name=criterion['node_name'])
                        if len(node) == 1:
                            nodegroup = str(node[0].nodegroup_id)
                        else:
                            nodegroup = ""
                            logger.warning("error finding specified node '{}'. criterion ignored.".format(criterion['node_name']))
                            continue

                        if not isinstance(criterion['value'], list):
                            criterion['value'] = [criterion['value']]

                        for value in criterion['value']:
                            try:
                                new_string_filter = Bool()
                                new_string_filter.must(Match(field='strings.string', query=value, type='phrase'))
                                new_string_filter.filter(Terms(field='strings.nodegroup_id', terms=[nodegroup]))

                                nested = Nested(path='strings', query=new_string_filter)

                                ## manual test to see if any criteria have been added to the query yet
                                if original_dsl['query']['match_all'] == {}:
                                    paramount.should(nested)
                                else:
                                    paramount.must(nested)

                            except Exception as e:
                                raise(e)

                ## add good types
                else:
                    paramount.should(Terms(field="graph_id", terms=doc_type))

        except Exception as e:
            print(e)
        return paramount


    def get_allowed_resource_ids(self, user, graphid, invert=False):
        """
        Returns the resourceinstanceids for all resources that a user is allowed to
        access. Optionally only gets ids from one graph. Set invert=True to return
        ids that the user is NOT allowed to access.
        """

        response = {
            "access_level": "",
            "id_list": []
        }

        match_terms = self.get_match_conditions(user, graphid)

        if match_terms == "no_access" or match_terms == "full_access":
            response["access_level"] = match_terms
            return response
        else:
            response["access_level"] = "partial_access"
            match_node = match_terms['node_name']
            match_value = match_terms['value']

        se = SearchEngineFactory().create()
        query = Query(se, start=0, limit=10000)
        query.include('graph_id')
        query.include('resourceinstanceid')

        node = Node.objects.filter(graph_id=graphid, name=match_node)
        if len(node) == 1:
            nodegroup = str(node[0].nodegroup_id)
        else:
            nodegroup = ""
            logger.warning("error finding specified node '{}'. criterion ignored.".format(match_node))
            return "no_access"

        if not isinstance(match_value, list):
            match_value = [match_value]

        paramount = Bool()
        for value in match_value:
            match_filter = Bool()
            match_filter.must(Match(field='strings.string', query=value, type='phrase'))
            match_filter.filter(Terms(field='strings.nodegroup_id', terms=[nodegroup]))
            container = Nested(path='strings', query=match_filter)
            paramount.should(container)

        query.add_query(paramount)

        if settings.LOG_LEVEL == "DEBUG":
            with open(os.path.join(settings.LOG_DIR, "allowed_resources_query.json"), "w") as output:
                output.write(str(query))

        results = query.search(index='resources', doc_type=graphid)

        resourceids = [i['_source']['resourceinstanceid'] for i in results['hits']['hits']]

        if invert is True:
            inverted_res = ResourceInstance.objects.filter(graph_id=graphid).exclude(resourceinstanceid__in=resourceids)
            resourceids = [i.resourceinstanceid for i in inverted_res]

        response["id_list"] = resourceids
        return response

    def make_management_area_geofilter(self, user, doc_type=None):

        # ultimately, find the areas or area groups for this user
        from fpan.models import ManagementArea
        ma = ManagementArea.objects.get(name="test")
        feature_geom = JSONDeserializer().deserialize(ma.geom.geojson)

        geoshape = GeoShape(
            field="geometries.geom.features.geometry",
            type=feature_geom["type"],
            coordinates=feature_geom["coordinates"]
        )

        spatial_query = Bool()
        spatial_query.filter(geoshape)
        if doc_type:
            spatial_query.filter(Terms(field="graph_id", terms=doc_type))


        search_query = Bool()
        search_query.filter(Nested(path="geometries", query=spatial_query))

        return search_query
