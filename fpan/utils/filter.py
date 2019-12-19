import os
import json
from django.conf import settings
from django.contrib.auth.models import Group, User
from arches.app.models.models import Node, GraphModel
from arches.app.models.resource import Resource
from arches.app.utils.betterJSONSerializer import JSONSerializer, JSONDeserializer
from arches.app.search import elasticsearch_dsl_builder as edb
from fpan.search.elasticsearch_dsl_builder import Type
from fpan.models.managedarea import ManagedArea

from .permission_backend import user_is_anonymous, user_is_scout, check_state_access

def apply_advanced_docs_permissions(dsl, request):

    docs_perms = settings.RESOURCE_MODEL_USER_RESTRICTIONS
    doc_types = get_doc_type(request)

    for doc in doc_types:

        rules = get_match_conditions(request.user, doc)

        if rules == "full_access":
            continue

        elif rules == "no_access":
            dsl = add_doc_specific_criterion(dsl, doc, doc_types, no_access=True)

        else:
            dsl = add_doc_specific_criterion(dsl, doc, doc_types, criterion=rules)

    return dsl

def get_match_conditions(user, graphid):

    # allow superuser admins to get full access to everything
    if user.is_superuser:
        return "full_access"

    docs_perms = settings.RESOURCE_MODEL_USER_RESTRICTIONS
    # assume full access if there is no condition in the settings.
    if graphid not in docs_perms:
        return "full_access"

    ## standard, basic check to apply restrictions to public users
    if user_is_anonymous(user):
        perm_settings = docs_perms[graphid]['public']

    ## alternative, FPAN-specific scenarios
    elif user_is_scout(user):
        perm_settings = docs_perms[graphid]['scout']

    # special handling of the state land manager permissions here
    elif check_state_access(user):
        filter_config = get_state_node_match(user)
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
        # the node named above.
        if perm_settings['match_config']['match_to'] == "<username>":
            filter_config['value'] = user.username

        # generic allowance for specific, non-user-derived values to be passed in
        else:
            filter_config['value'] = filter_config['match_config']['match_to']

    return filter_config

def get_state_node_match(user):

    # The FL_BAR user gets full access to all sites
    if user.groups.filter(name="FL_BAR").exists():
        return False

    # The FMSF user gets full access to all sites
    if user.groups.filter(name="FMSF").exists():
        return False

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
            except:
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

        return {
            'node_name': "Managing Agency",
            'value': "FL Fish and Wildlife Conservation Commission"
        }

    elif user.groups.filter(name="FL_AquaticPreserve").exists():

        return {
            'node_name': "Managing Agency",
            'value': "FL Dept. of Environmental Protection, Florida Coastal Office"
        }

    else:
        print "non state park"

def add_doc_specific_criterion(dsl, spec_type, all_types, no_access=False, criterion=False):

    print "adding criterion:"
    print criterion

    paramount = edb.Bool()
    for doc_type in all_types:

        ## add special string filter for specified node in type
        if doc_type == spec_type:

            ## if no_access is the permission level for the user, exclude doc
            if no_access is True:
                print "restricting access"
                paramount.must_not(Type(type=doc_type))
                continue

            elif criterion is not False:
                node = Node.objects.filter(graph_id=spec_type,name=criterion['node_name'])
                if len(node) == 1:
                    nodegroup = str(node[0].nodegroup_id)
                else:
                    nodegroup = ""
                    print "error finding specified node '{}', criterion ignored".format(criterion['node_name'])
                    continue

                if not isinstance(criterion['value'], list):
                    criterion['value'] = [criterion['value']]

                for value in criterion['value']:
                    new_string_filter = edb.Bool()
                    new_string_filter.must(edb.Match(field='strings.string', query=value, type='phrase'))
                    new_string_filter.filter(edb.Terms(field='strings.nodegroup_id', terms=[nodegroup]))

                    nested = edb.Nested(path='strings', query=new_string_filter)

                    ## manual test to see if any criteria have been added to the query yet
                    f = dsl._dsl['query']['bool']['filter']
                    m = dsl._dsl['query']['bool']['must']
                    mn = dsl._dsl['query']['bool']['must_not']
                    s = dsl._dsl['query']['bool']['should']

                    ## if they have, then the new statement needs to be MUST
                    if f or m or mn or s:
                        paramount.must(nested)

                    ## otherwise, use SHOULD
                    else:
                        paramount.should(nested)

        ## add good types
        else:
            paramount.should(Type(type=doc_type))

    dsl.add_query(paramount)
    return dsl

def get_doc_type(request):

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
            all_rm_ids = GraphModel.objects.filter(isresource=True).values_list('graphid', flat=True)
            use_ids = [str(i) for i in all_rm_ids if not str(i) in neg_filters]

    else:
        resource_models = GraphModel.objects.filter(isresource=True).values_list('graphid', flat=True)
        use_ids = [str(i) for i in resource_models]

    if len(use_ids) == 0:
        ret = []
    else:
        ret = list(set(use_ids))
    return ret
