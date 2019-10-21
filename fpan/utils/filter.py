from django.conf import settings
from arches.app.models.models import Node, GraphModel
from arches.app.utils.betterJSONSerializer import JSONSerializer, JSONDeserializer
from arches.app.search import elasticsearch_dsl_builder as edb
from fpan.search.elasticsearch_dsl_builder import Type

from .accounts import check_anonymous, check_scout_access, check_state_access

def get_perm_details(user,doc_type):

    term_filter = {}

    ## return false for admins to get full access to everything
    if user.is_superuser:
        return False
    
    ## return false if there are no user-based restrictions for this resource model
    if not doc_type in settings.RESOURCE_MODEL_USER_RESTRICTIONS.keys():
        return False
        
    elif check_state_access(user):
    
        print "this is a state USER"
    
        ## figure out what state group the user belongs to
        for sg in STATE_GROUP_NAMES:
            if user.groups.filter(name=sg).exists():
                state_group_name = sg
                break
        print "state group name:"
        print state_group_name

        ## return false for a few of the state agencies that get full access
        if state_group_name in ["FMSF","FL_BAR"]:
            return False
        else:
            term_filter = settings.RESOURCE_MODEL_USER_RESTRICTIONS[doc_type]['State']['term_filter']
        ## get full agency name to match with node value otherwise
        if state_group_name == "StatePark":
            term_filter['value'] = 'FL Dept. of Environmental Protection, Div. of Recreation and Parks'
        elif state_group_name == "FL_AquaticPreserve":
            term_filter['value'] = 'FL Dept. of Environmental Protection, Florida Coastal Office'
        elif state_group_name == "FL_Forestry":
            term_filter['value'] = 'FL Dept. of Agriculture and Consumer Services, Florida Forest Service'
        elif state_group_name == "FWC":
            term_filter['value'] = 'FL Fish and Wildlife Conservation Commission'
        else:
            print state_group_name + " not handled properly"
            
    elif check_scout_access(user):
        term_filter = settings.RESOURCE_MODEL_USER_RESTRICTIONS[doc_type]['Scout']['term_filter']
        term_filter['value'] = user.username
        
    elif check_anonymous(user):
        term_filter = settings.RESOURCE_MODEL_USER_RESTRICTIONS[doc_type]['default']['level']

    return term_filter

def add_doc_specific_criterion(dsl,spec_type,all_types,criterion={}):

    ## if there is no criterion to add, return original dsl
    if not criterion:
        return dsl
    print "adding criterion:"
    print criterion

    paramount = edb.Bool()
    for doc_type in all_types:

        ## add special string filter for specified node in type
        if doc_type == spec_type:

            ## if no_access is the permission level for the user, exclude doc
            if criterion == 'no_access':
                paramount.must_not(Type(type=doc_type))
                continue

            node = Node.objects.filter(graph_id=spec_type,name=criterion['node_name'])
            if len(node) == 1:
                nodegroup = str(node[0].nodegroup_id)
            else:
                nodegroup = ""
                print "error finding specified node '{}', criterion ignored".format(criterion['node_name'])
                return dsl

            new_string_filter = edb.Bool()
            new_string_filter.must(edb.Match(field='strings.string', query=criterion['value'], type='phrase'))
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

def apply_advanced_docs_permissions(dsl, request):

    docs_perms = settings.RESOURCE_MODEL_USER_RESTRICTIONS
    doc_types = get_doc_type(request)
    for doc in doc_types:
        if not doc in docs_perms.keys() or not 'default' in docs_perms[doc].keys():
            print "no ['default'] permissions for this resource model:{}".format(doc)
            continue

        level = docs_perms[doc]['default']['level']
        print level
        if level == "no_access":
            filter = "no_access"
        elif level == "term_filter":
            filter = docs_perms[doc]['default']['term_filter']
        else:
            continue

        filter = get_perm_details(request.user,doc)
        
        print "filter:", filter
        dsl = add_doc_specific_criterion(dsl, doc, doc_types, criterion=filter)

    return dsl