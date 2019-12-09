from arches.app.search.search_engine_factory import SearchEngineFactory
from arches.app.search.elasticsearch_dsl_builder import Query, Bool, Match, Terms, Nested
from arches.app.models.models import Node, ResourceInstance
from fpan.utils.filter import get_match_conditions


def user_can_edit_this_resource(user, resourceinstanceid):
    """
    Determines whether this user can edit this specific resource instance.
    Return True or False.
    """

    res = ResourceInstance.objects.get(resourceinstanceid=resourceinstanceid)
    ok_ids = get_allowed_resource_ids(user, res.graph_id)
    return resourceinstanceid in ok_ids


def get_allowed_resource_ids(user, graphid, invert=False):
    """
    Returns the resourceinstanceids for all resources that a user is allowed to
    access. Optionally only gets ids from one graph. Set invert=True to return
    ids that the user is NOT allowed to access.
    """

    match_terms = get_match_conditions(user, graphid)
    print "match_terms", match_terms
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
