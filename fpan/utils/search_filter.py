import os
import json
import logging
from django.contrib.auth.models import Group, User
from arches.app.models.models import Node, GraphModel
from arches.app.models.system_settings import settings
from arches.app.models.resource import Resource
from arches.app.utils.betterJSONSerializer import JSONSerializer, JSONDeserializer
from arches.app.search import elasticsearch_dsl_builder as edb
from .permission_backend import get_match_conditions

logger = logging.getLogger(__name__)

def make_management_area_geofilter(user, doc_type=None):

    # ultimately, find the areas or area groups for this user
    from fpan.models import ManagementArea
    ma = ManagementArea.objects.get(name="test")
    feature_geom = JSONDeserializer().deserialize(ma.geom.geojson)

    geoshape = edb.GeoShape(
        field="geometries.geom.features.geometry",
        type=feature_geom["type"],
        coordinates=feature_geom["coordinates"]
    )

    spatial_query = edb.Bool()
    spatial_query.filter(geoshape)
    if doc_type:
        spatial_query.filter(edb.Terms(field="graph_id", terms=doc_type))


    search_query = edb.Bool()
    search_query.filter(edb.Nested(path="geometries", query=spatial_query))


    return search_query


def add_doc_specific_criterion(original_dsl, spec_type, all_types, no_access=False, criterion=False):

    logger.debug("adding criterion: {} to {}".format(criterion, spec_type))

    paramount = edb.Bool()

    for doc_type in all_types:

        ## add special string filter for specified node in type
        if doc_type == spec_type:

            ## if no_access is the permission level for the user, exclude doc
            if no_access is True:
                logger.debug("restricting access to {}".format(doc_type))
                paramount.must_not(edb.Terms(field="graph_id", terms=doc_type))
                continue

            elif criterion is not False:
                node = Node.objects.filter(graph_id=spec_type,name=criterion['node_name'])
                if len(node) == 1:
                    nodegroup = str(node[0].nodegroup_id)
                else:
                    nodegroup = ""
                    logger.warning("error finding specified node '{}'. criterion ignored.".format(criterion['node_name']))
                    continue

                if not isinstance(criterion['value'], list):
                    criterion['value'] = [criterion['value']]

                for value in criterion['value']:
                    try:
                        new_string_filter = edb.Bool()
                        new_string_filter.must(edb.Match(field='strings.string', query=value, type='phrase'))
                        new_string_filter.filter(edb.Terms(field='strings.nodegroup_id', terms=[nodegroup]))

                        nested = edb.Nested(path='strings', query=new_string_filter)

                        ## manual test to see if any criteria have been added to the query yet
                        if original_dsl['query']['match_all'] == {}:
                            paramount.should(nested)
                        else:
                            paramount.must(nested)

                    except Exception as e:
                        raise(e)

        ## add good types
        else:
            paramount.should(edb.Terms(field="graph_id", terms=doc_type))

    return paramount
