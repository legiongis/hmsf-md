import time
import logging

from django.conf import settings

from arches.app.models.models import Node
from arches.app.models.resource import Resource
from arches.app.models.tile import Tile

from fpan.search.components.rule_filter import Rule, RuleFilter

logger = logging.getLogger(__name__)


def user_is_land_manager(user):
    return hasattr(user, "landmanager")


def user_is_scout(user):
    return hasattr(user, "scout")


def get_archaeological_site_rule(user) -> Rule:

    arch_graphid = settings.GRAPH_LOOKUP["as"]["id"]

    if user.is_superuser:
        rule = Rule("full_access", graph_id=arch_graphid)

    elif user_is_land_manager(user):
        if user.landmanager.site_access_mode == "FULL":
            rule = Rule("full_access", graph_id=arch_graphid)

        elif user.landmanager.site_access_mode == "AREA":
            ## this was supposed to be a proper geo rule as below, but
            ## that doesn't allow for arbitrary assignment of nearby
            ## management areas that don't spatially intersect.
            # multipolygon = user.landmanager.areas_as_multipolygon
            # rules["Archaeological Site"] = Rule(
            #   graph_name="Archaeological Site"
            #   geometry=multipolygon,
            # )

            ## instead, apply attribute rule based on the names of
            ## of associated areas.
            value = ["<no area set>"]
            if len(user.landmanager.all_areas) > 0:
                value = [f"{i.name} ({i.pk})" for i in user.landmanager.all_areas]
            rule = Rule(
                "attribute_filter",
                graph_id=arch_graphid,
                node_id=settings.SPATIAL_JOIN_NODE_LOOKUP["Archaeological Site"][
                    "area_nodeid"
                ],
                value=value,
            )

        elif user.landmanager.site_access_mode == "AGENCY":
            value = ["<no agency set>"]
            if user.landmanager.management_agency:
                value = [user.landmanager.management_agency.name]

            rule = Rule(
                "attribute_filter",
                graph_id=arch_graphid,
                node_id=settings.SPATIAL_JOIN_NODE_LOOKUP["Archaeological Site"][
                    "agency_nodeid"
                ],
                value=value,
            )
        elif user.site_access_mode == "NONE":
            rule = Rule("no_access", graph_id=arch_graphid)
        else:
            rule = Rule("no_access", graph_id=arch_graphid)

    elif user_is_scout(user):
        if user.scout.scoutprofile.site_access_mode == "FULL":
            rule = Rule("full_access", graph_id=arch_graphid)
        else:
            rule = Rule(
                "attribute_filter",
                graph_id=arch_graphid,
                node_id=settings.ARCHAEOLOGICAL_SITE_ASSIGNMENT_NODE_ID,
                value=[user.username, "anonymous"],
            )

    elif user.username == "anonymous":
        rule = Rule(
            "attribute_filter",
            graph_id=arch_graphid,
            node_id=settings.ARCHAEOLOGICAL_SITE_ASSIGNMENT_NODE_ID,
            value=[user.username],
        )
    else:
        rule = Rule("no_access", graph_id=arch_graphid)

    return rule


def get_scout_report_rule(user) -> Rule:

    report_graphid = settings.GRAPH_LOOKUP["sr"]["id"]
    arch_rule = get_archaeological_site_rule(user)

    start = time.time()

    if arch_rule.type == "full_access":
        return Rule("full_access", graph_id=report_graphid)
    elif arch_rule.type == "no_access":
        arch_ids = []
    else:
        ## get ids only for the sites this user has access to
        arch_ids = RuleFilter().get_resources_from_rule(arch_rule, ids_only=True)

    ## now add all ids for all Historic Cemeteries and Historic Structures
    cem_ids = list(
        Resource.objects.filter(
            graph__pk=settings.GRAPH_LOOKUP["hc"]["id"]
        ).values_list("pk", flat=True)
    )
    struct_ids = list(
        Resource.objects.filter(
            graph__pk=settings.GRAPH_LOOKUP["hs"]["id"]
        ).values_list("pk", flat=True)
    )

    resids = [str(i) for i in arch_ids + cem_ids + struct_ids]

    siteid_node = Node.objects.get(name="FMSF Site ID", graph__pk=report_graphid)
    siteid_nodeid = str(siteid_node.pk)
    rep_datas = Tile.objects.filter(nodegroup=siteid_node.nodegroup).values(
        "data", "resourceinstance_id"
    )
    reportids = []
    for rd in rep_datas:
        try:
            fmsfid = rd["data"][siteid_nodeid][0]["resourceId"]
            if fmsfid in resids:
                reportids.append(str(rd["resourceinstance_id"]))
        except (IndexError, KeyError, TypeError) as e:
            logger.warning(f"can't get fmsf id from {rd['resourceinstance_id']}")
            logger.warning(e)
        except Exception as e:
            logger.error(f"can't get fmsf id from {rd['resourceinstance_id']}")
            logger.error(e)

    logger.debug(f"get_scout_report_rule: {time.time() - start}")
    return Rule("resourceid_filter", resourceids=reportids)


def get_rule_by_graph(user, graphid=None) -> Rule:

    if graphid == settings.GRAPH_LOOKUP["as"]["id"]:
        return get_archaeological_site_rule(user)
    elif graphid == settings.GRAPH_LOOKUP["sr"]["id"]:
        return get_scout_report_rule(user)
    else:
        return Rule("full_access", graph_id=graphid)


def get_user_allowed_resources_by_graph(user, graphid):

    rule = get_rule_by_graph(user, graphid=graphid)
    if rule.type in ["full_access", "no_access"]:
        return []
    id_list = RuleFilter().get_resources_from_rule(rule)
    return id_list


def generate_site_access_html(user):
    """This function should be called by a context_processor to dynamically generate HTML
    content that is used in the rule filter component template. It can be altered as needed."""

    ## ultimately, this should be dynamically driven directly by the rules this filter finds.
    ## for now though, there is a lot of hard-coded HMS logic

    FULL_ACCESS_HTML = "<p>Your account has full access to <strong>all</strong> archaeological sites.</p>"
    NO_ACCESS_HTML = (
        "<p>Your account does not have access to any archaeological sites.</p>"
    )

    if user.is_superuser:
        return FULL_ACCESS_HTML
    if user.username == "anonymous":
        return NO_ACCESS_HTML

    if user_is_scout(user):
        if user.scout.scoutprofile.site_access_mode == "FULL":
            return FULL_ACCESS_HTML
        elif user.scout.scoutprofile.site_access_mode == "USERNAME=ASSIGNEDTO":
            return "<p>You have access to any archaeological sites to which you have been individually assigned.</p>"
        else:
            return NO_ACCESS_HTML

    if user_is_land_manager(user):
        if user.landmanager.site_access_mode == "FULL":
            html = FULL_ACCESS_HTML
        elif user.landmanager.site_access_mode == "AREA":
            html = "<p>You can access any archaeological sites that are located in the following Management Areas:</p>"
            if len(user.landmanager.all_areas) == 0:
                html += "<p><em>No Management Areas have been added to your Land Manager profile.</em></p>"
            else:
                html += (
                    "<ul style='list-style:none; padding-left:0px; font-weight:bold;'>"
                )
                for group in user.landmanager.grouped_areas.all():
                    html += f"<li>{group.name} (grouped area)</li>"
                for area in user.landmanager.individual_areas.all():
                    html += f"<li>{area.name}</li>"
                html += "</ul>"
        elif user.landmanager.site_access_mode == "AGENCY":
            html = f"<p>You can access any archaeological sites that are managed by your agency: <strong>{user.landmanager.management_agency}</strong></p>"
        else:
            html = NO_ACCESS_HTML

        return html
