import logging
from typing import TYPE_CHECKING

from django.conf import settings

from arches.app.search.elasticsearch_dsl_builder import Bool, Terms
from arches.app.search.components.base import BaseSearchFilter
from arches.app.search.mappings import RESOURCES_INDEX
from arches.app.models.models import Node
from arches.app.models.tile import Tile

from .rule_filter import save_dsl

logger = logging.getLogger(__name__)

details = {
    "searchcomponentid": "ade4886d-0000-4cd5-ac30-5b1eb6e3bef3",
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
    def append_dsl(self, search_query_object, **kwargs):
        """
        This is the method that Arches calls, and ultimately all it does is

          search_results_object["query"].add_query(some_new_es_dsl)

        Only proceed with the replacement of the query if the filter is enabled.
        """

        if TYPE_CHECKING and not self.request:
            return

        if self.request.GET.get(details["componentname"]) == "enabled":
            if settings.LOG_LEVEL == "DEBUG":
                save_dsl(
                    search_query_object["query"]._dsl,
                    f"{self.componentname}_dsl__before.json",
                )

            # get original results here, and iterate them to get the ids to look for
            # in Scout Reports
            search_query_object["query"].limit = 10000
            results = search_query_object["query"].search(index=RESOURCES_INDEX)
            resids = [
                i["_source"]["resourceinstanceid"] for i in results["hits"]["hits"]
            ]

            # now look through all Scout Report tiles to return ids of the ones that reference
            # the sites from the query.
            site_node = Node.objects.get(
                name="FMSF Site ID", graph_id=settings.GRAPH_LOOKUP["sr"]["id"]
            )
            report_siteid_tiles = Tile.objects.filter(
                resourceinstance__graph_id=settings.GRAPH_LOOKUP["sr"]["id"],
                nodegroup=site_node.nodegroup,
                data__has_key=str(site_node.pk),
            ).values_list("resourceinstance_id", "data")

            reportids_set = set()
            for t in report_siteid_tiles:
                try:
                    if t[1][str(site_node.pk)][0]["resourceId"] in resids:
                        reportids_set.add(str(t[0]))
                except IndexError:
                    pass

            new_bool = Bool()
            terms = Terms(field="resourceinstanceid", terms=list(reportids_set))
            new_bool.must(terms)

            # replace original query object with new query
            search_query_object["query"].add_query(new_bool)

            if settings.LOG_LEVEL == "DEBUG":
                save_dsl(
                    search_query_object["query"]._dsl,
                    f"{self.componentname}_dsl__after.json",
                )
