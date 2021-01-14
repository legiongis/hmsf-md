import os
import json
import logging
from arches.app.utils.betterJSONSerializer import JSONDeserializer
from arches.app.search.elasticsearch_dsl_builder import Bool, Terms, GeoShape, Nested
from arches.app.search.components.base import BaseSearchFilter
from arches.app.models.system_settings import settings
from arches.app.models.models import GraphModel
from arches.app.utils.betterJSONSerializer import JSONSerializer, JSONDeserializer
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

        ## Should always be enabled. If not, raise exception.
        if querystring_params != "enabled":
            raise(Exception("Site filter is registered but not shown as enabled."))

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
            print("\n\n")
            print(e)
            logger.debug(e)


    def get_doc_types(self, request):

        all_resource_graphids = (
            GraphModel.objects.exclude(pk=settings.SYSTEM_SETTINGS_RESOURCE_MODEL_ID)
            .exclude(isresource=False)
            .exclude(isactive=False)
        ).values_list('graphid', flat=True)

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
                use_ids = [str(i) for i in all_resource_graphids if not str(i) in neg_filters]

        else:
            use_ids = [str(i) for i in all_resource_graphids]

        if len(use_ids) == 0:
            ret = []
        else:
            ret = list(set(use_ids))
        return ret
