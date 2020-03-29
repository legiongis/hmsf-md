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

def apply_advanced_docs_permissions(original_dsl, request):

    docs_perms = settings.RESOURCE_MODEL_USER_RESTRICTIONS
    doc_types = get_doc_type(request)

    clause = None
    for doc in doc_types:

        rules = get_match_conditions(request.user, doc)
        if rules == "full_access":
            continue

        elif rules == "no_access":
            clause = add_doc_specific_criterion(original_dsl, doc, doc_types, no_access=True)

        else:
            clause = add_doc_specific_criterion(original_dsl, doc, doc_types, criterion=rules)

    return clause


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

def get_doc_type(request):

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
        print(use_ids)

    if len(use_ids) == 0:
        ret = []
    else:
        ret = list(set(use_ids))
    return ret
