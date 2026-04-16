import time
import logging

from django.conf import settings

from arches.app.models.models import GraphModel, Node
from arches.app.models.resource import Resource
from arches.app.models.tile import Tile

from fpan.search.components.rule_filter import Rule, RuleFilter

logger = logging.getLogger(__name__)


def user_is_land_manager(user):
    return hasattr(user, "landmanager")


def user_is_scout(user):
    return hasattr(user, "scout")


def report_rule_from_arch_rule(arch_rule):
    """
    Utility function that returns a resourceid filter that contains all
    resourceids for Scout Reports attached to Archaeological Sites
    that fit the specified archaeological site filter.
    """
    start = time.time()
    if arch_rule.type == "full_access":
        return Rule("full_access", graph_name="Scout Report")
    elif arch_rule.type == "no_access":
        arch_ids = []
    else:
        ## get ids only for the sites this user has access to
        arch_ids = RuleFilter().get_resources_from_rule(arch_rule, ids_only=True)

    ## now add all ids for all Historic Cemeteries and Historic Structures
    cem_graph = GraphModel.objects.get(name="Historic Cemetery")
    cem_ids = list(
        Resource.objects.filter(graph=cem_graph).values_list("pk", flat=True)
    )
    struct_graph = GraphModel.objects.get(name="Historic Structure")
    struct_ids = list(
        Resource.objects.filter(graph=struct_graph).values_list("pk", flat=True)
    )

    resids = [str(i) for i in arch_ids + cem_ids + struct_ids]

    report_graph = GraphModel.objects.get(name="Scout Report")
    siteid_node = Node.objects.get(name="FMSF Site ID", graph=report_graph)
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

    report_rule = Rule("resourceid_filter", resourceids=reportids)
    logger.debug(f"report_rule_from_arch_rule: {time.time() - start}")
    return report_rule


def get_rule_by_graph(user, graphid=None, graph_name=None) -> Rule:

    if not graph_name:
        graph_name = GraphModel.objects.get(graphid=graphid).name

    if user.is_superuser:
        rule = Rule("full_access", graph_name=graph_name)

    elif user_is_land_manager(user):
        if graph_name == "Archaeological Site":
            if user.site_access_mode == "FULL":
                rule = Rule("full_access", graph_name=graph_name)

            elif user.site_access_mode == "AREA":
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
                if len(user.all_areas) > 0:
                    value = [f"{i.name} ({i.pk})" for i in user.all_areas]
                rule = Rule(
                    "attribute_filter",
                    graph_name="Archaeological Site",
                    node_id=settings.SPATIAL_JOIN_NODE_LOOKUP["Archaeological Site"][
                        "area_nodeid"
                    ],
                    value=value,
                )

            elif user.site_access_mode == "AGENCY":
                value = ["<no agency set>"]
                if user.management_agency:
                    value = [user.management_agency.name]

                rule = Rule(
                    "attribute_filter",
                    graph_name="Archaeological Site",
                    node_id=settings.SPATIAL_JOIN_NODE_LOOKUP["Archaeological Site"][
                        "agency_nodeid"
                    ],
                    value=value,
                )
            elif user.site_access_mode == "NONE":
                rule = Rule("no_access", graph_name=graph_name)
            else:
                rule = Rule("no_access", graph_name=graph_name)

        elif graph_name == "Scout Report":
            arch_rule = get_rule_by_graph(user, graph_name="Archaeological Site")
            rule = report_rule_from_arch_rule(arch_rule)

        else:
            rule = Rule("full_access", graph_name=graph_name)

    elif user_is_scout(user):
        if graph_name == "Archaeological Site":
            if user.scout.scoutprofile.site_access_mode == "FULL":
                rule = Rule("full_access", graph_name=graph_name)
            else:
                rule = Rule(
                    "attribute_filter",
                    graph_name="Archaeological Site",
                    node_id=settings.ARCHAEOLOGICAL_SITE_ASSIGNMENT_NODE_ID,
                    value=[user.username, "anonymous"],
                )

        elif graph_name == "Scout Report":
            arch_rule = get_rule_by_graph(user, graph_name="Archaeological Site")
            rule = report_rule_from_arch_rule(arch_rule)

        else:
            rule = Rule("full_access", graph_name=graph_name)

        return rule

    elif user.username == "anonymous":
        ## manual handling of public users here
        if graph_name == "Archaeological Site":
            rule = Rule(
                "attribute_filter",
                graph_name=graph_name,
                node_id=settings.ARCHAEOLOGICAL_SITE_ASSIGNMENT_NODE_ID,
                value=[user.username],
            )

        elif graph_name == "Scout Report":
            arch_rule = get_rule_by_graph(user, graph_name="Archaeological Site")
            rule = report_rule_from_arch_rule(arch_rule)

        else:
            rule = Rule("full_access", graph_name=graph_name)

    else:
        # this will catch old land managers before their profiles
        # have been created.
        logger.debug(f"get_rule_by_graph: user {user.username} is adrift.")
        if graph_name in ["Archaeological Site", "Scout Report"]:
            rule = Rule("no_access", graph_name=graph_name)
        else:
            rule = Rule("full_access", graph_name=graph_name)

    return rule


def get_user_allowed_resources_by_graph(user, graphid=None, graph_name=None):

    if not graph_name:
        graph_name = GraphModel.objects.get(graphid=graphid).name

    rule = get_rule_by_graph(user, graph_name=graph_name)
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
