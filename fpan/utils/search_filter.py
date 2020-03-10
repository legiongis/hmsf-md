import os
import json
import logging
from django.conf import settings
from django.contrib.auth.models import Group, User
from arches.app.models.models import Node, GraphModel
from arches.app.models.resource import Resource
from arches.app.utils.betterJSONSerializer import JSONSerializer, JSONDeserializer
from arches.app.search import elasticsearch_dsl_builder as edb
from fpan.search.elasticsearch_dsl_builder import Type
from .permission_backend import get_match_conditions

logger = logging.getLogger(__name__)

def apply_advanced_docs_permissions(dsl, request):

    docs_perms = settings.RESOURCE_MODEL_USER_RESTRICTIONS
    doc_types = get_doc_type(request)

    for doc in doc_types:

        rules = get_match_conditions(request.user, doc)

        if rules == "full_access":
            continue

        elif rules == "no_access":
            dsl = add_doc_specific_criterion(dsl, doc, doc_types, no_access=True)

        else:
            dsl = add_doc_specific_criterion(dsl, doc, doc_types, criterion=rules)

    return dsl


def add_doc_specific_criterion(dsl, spec_type, all_types, no_access=False, criterion=False):

    logger.debug("adding criterion: {} to {}".format(criterion, spec_type))

    paramount = edb.Bool()
    for doc_type in all_types:

        ## add special string filter for specified node in type
        if doc_type == spec_type:

            ## if no_access is the permission level for the user, exclude doc
            if no_access is True:
                logger.debug("restricting access to {}".format(doc_type))
                paramount.must_not(Type(type=doc_type))
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
                    new_string_filter = edb.Bool()
                    new_string_filter.must(edb.Match(field='strings.string', query=value, type='phrase'))
                    new_string_filter.filter(edb.Terms(field='strings.nodegroup_id', terms=[nodegroup]))

                    nested = edb.Nested(path='strings', query=new_string_filter)

                    ## manual test to see if any criteria have been added to the query yet
                    f = dsl._dsl['query']['bool']['filter']
                    m = dsl._dsl['query']['bool']['must']
                    mn = dsl._dsl['query']['bool']['must_not']
                    s = dsl._dsl['query']['bool']['should']

                    ## if they have, then the new statement needs to be MUST
                    if f or m or mn or s:
                        paramount.must(nested)

                    ## otherwise, use SHOULD
                    else:
                        paramount.should(nested)

        ## add good types
        else:
            paramount.should(Type(type=doc_type))

    dsl.add_query(paramount)
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
