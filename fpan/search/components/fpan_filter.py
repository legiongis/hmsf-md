from arches.app.utils.betterJSONSerializer import JSONDeserializer
from arches.app.search.elasticsearch_dsl_builder import Bool, Terms
from arches.app.search.components.base import BaseSearchFilter

details = {
    "searchcomponentid": "",
    "name": "FPAN Filter",
    "icon": "",
    "modulename": "fpan_filter.py",
    "classname": "FPANFilter",
    "type": "fpan-filter",
    "componentpath": "views/components/search/fpan-filter",
    "componentname": "fpan-filter",
    "sortorder": "0",
    "enabled": True,
}


class FPANFilter(BaseSearchFilter):
    def append_dsl(self, search_results_object, permitted_nodegroups, include_provisional):
        print("uin PFAN p[orna")
        search_query = Bool()
        querysting_params = self.request.GET.get(details["componentname"], "")

        graph_ids = []
        for resouceTypeFilter in JSONDeserializer().deserialize(querysting_params):
            graph_ids.append(str(resouceTypeFilter["graphid"]))

        terms = Terms(field="graph_id", terms=graph_ids)
        if resouceTypeFilter["inverted"] is True:
            search_query.must_not(terms)
        else:
            search_query.filter(terms)

        search_results_object["query"].add_query(search_query)
