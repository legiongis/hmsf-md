from arches.app.search.search_engine_factory import SearchEngineFactory
from arches.app.search.elasticsearch_dsl_builder import Query, Bool, Match, Terms, Nested
from arches.app.models.models import Node, ResourceInstance
from hms.models import Scout
from fpan.models import ManagedArea
from arches.app.models.system_settings import settings
settings.update_from_db()
# from fpan.utils.filter import get_match_conditions


def user_is_anonymous(user):
    return user.username == 'anonymous'


def check_state_access(user):
    state_user = user.groups.filter(name="Land Manager").exists()
    if user.is_superuser:
        state_user = True
    return state_user


def user_is_scout(user):
    try:
        scout = user.scout
        is_scout = True
    except Scout.DoesNotExist:
        is_scout = False
    return is_scout


def user_can_edit_this_resource(user, resourceinstanceid):
    """
    Determines whether this user can edit this specific resource instance.
    Return True or False.
    """

    res = ResourceInstance.objects.get(resourceinstanceid=resourceinstanceid)
    ok_ids = get_allowed_resource_ids(user, res.graph_id)
    if ok_ids == "full_access":
        return True
    elif ok_ids == "no_access":
        return False
    else:
        return resourceinstanceid in ok_ids


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


def get_allowed_resource_ids(user, graphid, invert=False):
    """
    Returns the resourceinstanceids for all resources that a user is allowed to
    access. Optionally only gets ids from one graph. Set invert=True to return
    ids that the user is NOT allowed to access.
    """

    match_terms = get_match_conditions(user, graphid)
    if match_terms == "no_access" or match_terms == "full_access":
        return match_terms
    else:
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
        print "error finding specified node '{}', criterion ignored".format(match_node)
        return "no_access"

    if not isinstance(match_value, list):
        match_value = [match_value]

    for value in match_value:
        match_filter = Bool()
        match_filter.must(Match(field='strings.string', query=value, type='phrase'))
        match_filter.filter(Terms(field='strings.nodegroup_id', terms=[nodegroup]))
        container = Nested(path='strings', query=match_filter)

    query.add_query(container)
    print query
    results = query.search(index='resource', doc_type=graphid)

    resourceids = [i['_source']['resourceinstanceid'] for i in results['hits']['hits']]

    if invert is True:
        inverted_res = ResourceInstance.objects.filter(graph_id=graphid).exclude(resourceinstanceid__in=resourceids)
        return [i.resourceinstanceid for i in inverted_res]

    return resourceids
