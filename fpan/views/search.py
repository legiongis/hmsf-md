from django.utils.translation import ugettext as _
from django.http import HttpResponseNotFound

from arches.app.models.system_settings import settings
from arches.app.models.models import GraphModel
from arches.app.utils.response import JSONResponse
from arches.app.utils.betterJSONSerializer import JSONSerializer, JSONDeserializer

from arches.app.views.search import SearchView
from arches.app.views.search import build_search_results_dsl
from arches.app.utils.pagination import get_paginator
from arches.app.views.search import get_nodegroups_by_datatype_and_perm
from arches.app.views.search import get_permitted_nodegroups, select_geoms_for_results
from arches.app.search.elasticsearch_dsl_builder import Bool, Match, Query, Nested, Term, Terms, GeoShape, Range, MinAgg, MaxAgg, RangeAgg, Aggregation, GeoHashGridAgg, GeoBoundsAgg, FiltersAgg, NestedAgg
from fpan.utils.permission_backend import get_allowed_resource_ids
from fpan.utils.filter import apply_advanced_docs_permissions

# from fpan.utils.filter import apply_advanced_docs_permissions, get_doc_type

class FPANSearchView(SearchView):

    def get(self, request):
        return super(FPANSearchView, self).get(request)

def exclude_resource_instances(dsl, id_list):

    exclude_clause = Bool()

    for resid in id_list:
        id_filter = Bool()
        exclude_clause.must_not(Match(field='resourceinstanceid', query=str(resid)))

    dsl.add_query(exclude_clause)
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

def search_results(request):

    try:
        search_results_dsl = build_search_results_dsl(request)
    except Exception as err:
        return JSONResponse(err.message, status=500)

    dsl = search_results_dsl['query']
    search_buffer = search_results_dsl['search_buffer']
    dsl.include('graph_id')
    dsl.include('root_ontology_class')
    dsl.include('resourceinstanceid')
    dsl.include('points')
    dsl.include('geometries')
    dsl.include('displayname')
    dsl.include('displaydescription')
    dsl.include('map_popup')
    dsl.include('provisional_resource')
    if request.GET.get('tiles', None) is not None:
        dsl.include('tiles')

    dsl = apply_advanced_docs_permissions(dsl, request)
    # excludeids = get_allowed_resource_ids(request.user, "f212980f-d534-11e7-8ca8-94659cf754d0", invert=True)

    # if isinstance(excludeids, list) and len(excludeids) > 0:
    #     dsl = exclude_resource_instances(dsl, excludeids)

    # else:
        # it's possible that excludeids could equal "no_access" or "full_access" but that's actually
        # redundant at this point, so just ignoring those scenarios for now.
        # pass

    results = dsl.search(index='resource', doc_type=get_doc_type(request))

    if results is not None:
        user_is_reviewer = request.user.groups.filter(name='Resource Reviewer').exists()
        total = results['hits']['total']
        page = 1 if request.GET.get('page') == '' else int(request.GET.get('page', 1))

        paginator, pages = get_paginator(request, results, total, page, settings.SEARCH_ITEMS_PER_PAGE)
        page = paginator.page(page)

        # only reuturn points and geometries a user is allowed to view
        geojson_nodes = get_nodegroups_by_datatype_and_perm(request, 'geojson-feature-collection', 'read_nodegroup')
        permitted_nodegroups = get_permitted_nodegroups(request.user)

        for result in results['hits']['hits']:
            result['_source']['points'] = select_geoms_for_results(result['_source']['points'], geojson_nodes, user_is_reviewer)
            result['_source']['geometries'] = select_geoms_for_results(result['_source']['geometries'], geojson_nodes, user_is_reviewer)
            try:
                permitted_tiles = []
                for tile in result['_source']['tiles']:
                    if tile['nodegroup_id'] in permitted_nodegroups:
                        permitted_tiles.append(tile)
                result['_source']['tiles'] = permitted_tiles
            except KeyError:
                pass

        ret = {}
        ret['results'] = results
        ret['search_buffer'] = JSONSerializer().serialize(search_buffer) if search_buffer != None else None
        ret['paginator'] = {}
        ret['paginator']['current_page'] = page.number
        ret['paginator']['has_next'] = page.has_next()
        ret['paginator']['has_previous'] = page.has_previous()
        ret['paginator']['has_other_pages'] = page.has_other_pages()
        ret['paginator']['next_page_number'] = page.next_page_number() if page.has_next() else None
        ret['paginator']['previous_page_number'] = page.previous_page_number() if page.has_previous() else None
        ret['paginator']['start_index'] = page.start_index()
        ret['paginator']['end_index'] = page.end_index()
        ret['paginator']['pages'] = pages
        ret['reviewer'] = user_is_reviewer

        return JSONResponse(ret)
    else:
        return HttpResponseNotFound(_("There was an error retrieving the search results"))
