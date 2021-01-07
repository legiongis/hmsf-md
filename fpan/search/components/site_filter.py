import os
import json
import logging
from arches.app.utils.betterJSONSerializer import JSONDeserializer
from arches.app.search.elasticsearch_dsl_builder import Bool, Terms, GeoShape, Nested
from arches.app.search.components.base import BaseSearchFilter
from arches.app.models.system_settings import settings
from fpan.utils.search_filter import apply_advanced_docs_permissions

logger = logging.getLogger(__name__)

details = {
    "searchcomponentid": "",
    "name": "Site Filter",
    "icon": "fa fa-key",
    "modulename": "site_filter.py",
    "classname": "SiteFilter",
    "type": "popup",
    "componentpath": "views/components/search/site-filter",
    "componentname": "site-filter",
    "sortorder": "0",
    "enabled": True,
}


class SiteFilter(BaseSearchFilter):
    def append_dsl(self, search_results_object, permitted_nodegroups, include_provisional):

        original_dsl = search_results_object["query"]._dsl
        if settings.LOG_LEVEL == "DEBUG":
            with open(os.path.join(settings.LOG_DIR, "dsl_before_fpan.json"), "w") as output:
                json.dump(original_dsl, output, indent=1)

        querystring_params = self.request.GET.get(details["componentname"], "")

        ## this will only be the case for superusers, and the FMSF and FL_BAR accounts.
        ## in this case no extra filter will be added to the query
        if querystring_params == "disabled":
            return

        ## this will be the vast majority of cases
        elif querystring_params == "enabled":
            try:

                search_query = apply_advanced_docs_permissions(original_dsl, self.request)

                if not search_query is None:
                    search_results_object["query"].add_query(search_query)

                # coords = [[[-81.477111876252,29.133006285427328],[-81.47314589490625,28.67123161923965],[-81.06663280694531,28.667751860292498],[-81.07258177896466,29.134738397156326],[-81.477111876252,29.133006285427328]]]
                # geoshape = GeoShape(
                #     field="geometries.geom.features.geometry", type="Polygon", coordinates=coords
                # )
                #
                # try:
                #     self.request.user.ManagerProfile
                # except Exception as e:
                #     print(e)
                #
                #
                # spatial_query = Bool()
                # spatial_query.filter(geoshape)
                #
                # search_query = Bool()
                # search_query.filter(Nested(path="geometries", query=spatial_query))
                #
                # search_results_object["query"].add_query(search_query)
                # print(search_results_object["query"])

                if settings.LOG_LEVEL == "DEBUG":
                    with open(os.path.join(settings.LOG_DIR, "dsl_after_fpan.json"), "w") as output:
                        json.dump(search_results_object["query"]._dsl, output, indent=1)

            except Exception as e:
                logger.debug(e)

        ## play it super safe and raise an exception here, which would be caused by
        ## a problem in the upstream javascript
        else:
            raise Exception
