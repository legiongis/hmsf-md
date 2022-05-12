import logging

from arches.app.search.search_engine_factory import SearchEngineFactory
from arches.app.search.elasticsearch_dsl_builder import Bool, Terms, Query
from arches.app.search.components.base import BaseSearchFilter
from arches.app.search.mappings import RESOURCES_INDEX
from arches.app.models.models import Node
from arches.app.models.tile import Tile

logger = logging.getLogger(__name__)

details = {
    "searchcomponentid": "",
    "name": "Scout Report Filter",
    "icon": "fa fa-binoculars",
    "modulename": "scout_report_filter.py",
    "classname": "ScoutReportFilter",
    "type": "popup",
    "componentpath": "views/components/search/scout-report-filter",
    "componentname": "scout-report-filter",
    "sortorder": "100",
    "enabled": True,
}

class ScoutReportFilter(BaseSearchFilter):

    def append_dsl(self, search_results_object, permitted_nodegroups, include_provisional):
        """
        This is the method that Arches calls, and ultimately all it does is

          search_results_object["query"].add_query(some_new_es_dsl)

        Only proceed with the replacement of the query if the filter is enabled.
        """

        if self.request.GET.get(details["componentname"]) == "enabled":

            # get original results here, and iterate them to get the ids to look for
            # in Scout Reports
            search_results_object["query"].limit = 10000
            results = search_results_object["query"].search(index=RESOURCES_INDEX)
            resids = set([i['_source']['resourceinstanceid'] for i in results['hits']['hits']])

            # now look through all Scout Report tiles to return ids of the ones that reference
            # the sites from the query.
            site_node = Node.objects.get(name="FMSF Site ID", graph__name="Scout Report")
            report_tiles = Tile.objects.filter(resourceinstance__graph__name="Scout Report", nodegroup=site_node.nodegroup)
            reportids = []
            for t in report_tiles:
                if len(t.data[str(site_node.pk)]) > 0:
                    if t.data[str(site_node.pk)][0]['resourceId'] in resids:
                        reportids.append(str(t.resourceinstance_id))

            # create new query using ids for the scout reports
            se = SearchEngineFactory().create()
            query = Query(se, limit=10000)

            new_bool = Bool()
            terms = Terms(
                field='resourceinstanceid',
                terms=reportids
            )
            new_bool.must(terms)
            query.add_query(new_bool)

            # replace original query object with new query
            search_results_object["query"] = query
