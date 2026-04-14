import json

from django.conf import settings
from django.contrib.auth.models import User

from hms.models import (
    ManagementArea,
    ManagementAgency,
    ManagementAreaGroup,
    ManagementAreaCategory,
)
from fpan.search.components.rule_filter import RuleFilter


def debug(request):
    return {
        "debug": settings.DEBUG,
        "plausible_site_domain": settings.PLAUSIBLE_SITE_DOMAIN,
        "plausible_embed_link": settings.PLAUSIBLE_EMBED_LINK,
    }


def username_widget_data(request):

    # only collect this information for a few specific views
    widget_views = ["resource", "graph_designer", "report", "add-resource"]

    username_dropdown_list = []

    if any([True for i in widget_views if i in request.path.split("/")]):
        username_dropdown_list = [
            {
                "id": str(i[0]),
                "selected": "false",
                "text": str(i[1]),
                "value": str(i[0]),
            }
            for i in User.objects.all()
            .order_by("username")
            .values_list("pk", "username")
        ]

    serialized_list = json.dumps(username_dropdown_list)
    return {"username_dropdown_list": serialized_list}


def management_area_importer_configs(request):

    return {
        "ma_group_opts": ManagementAreaGroup.objects.all()
        .order_by("name")
        .values("id", "name"),
        "ma_category_opts": ManagementAreaCategory.objects.all()
        .order_by("name")
        .values("id", "name"),
        "ma_agency_opts": ManagementAgency.objects.all()
        .order_by("name")
        .values("code", "name"),
        "ma_level_opts": ManagementArea._meta.get_field("management_level").choices,
    }


def rule_filter_html(request):
    return {"rule_filter_html": RuleFilter().generate_html(request.user)}
