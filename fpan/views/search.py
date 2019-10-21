from django.utils.translation import ugettext as _
from django.http import HttpResponseNotFound

from arches.app.models.system_settings import settings
from arches.app.utils.response import JSONResponse
from arches.app.utils.betterJSONSerializer import JSONSerializer, JSONDeserializer

from arches.app.views.search import SearchView
from arches.app.views.search import build_search_results_dsl
from arches.app.utils.pagination import get_paginator
from arches.app.views.search import get_nodegroups_by_datatype_and_perm
from arches.app.views.search import get_permitted_nodegroups, select_geoms_for_results

from fpan.utils.filter import apply_advanced_docs_permissions, get_doc_type

class FPANSearchView(SearchView):

    def get(self, request):
        print "new search thing"
        return super(FPANSearchView, self).get(request)

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
