from arches.app.utils.betterJSONSerializer import JSONDeserializer
from arches.app.search.elasticsearch_dsl_builder import Bool, Terms
from arches.app.search.components.base import BaseSearchFilter

details = {
    "searchcomponentid": "",
    "name": "Site Filter",
    "icon": "",
    "modulename": "site_filter.py",
    "classname": "SiteFilter",
    "type": "site-filter",
    "componentpath": "views/components/search/site-filter",
    "componentname": "site-filter",
    "sortorder": "0",
    "enabled": True,
}


class SiteFilter(BaseSearchFilter):
    def append_dsl(self, search_results_object, permitted_nodegroups, include_provisional):
        print("APPENDING FPAN DSL")

        try:
            search_query = Bool()
            querysting_params = self.request.GET.get(details["componentname"], "")
            print(querysting_params)
            # graph_ids = []
            # for resouceTypeFilter in JSONDeserializer().deserialize(querysting_params):
            #     graph_ids.append(str(resouceTypeFilter["graphid"]))
            #
            # terms = Terms(field="graph_id", terms=graph_ids)
            # if resouceTypeFilter["inverted"] is True:
            #     search_query.must_not(terms)
            # else:
            #     search_query.filter(terms)

            search_results_object["query"].add_query(search_query)
        except Exception as e:
            print(e)
