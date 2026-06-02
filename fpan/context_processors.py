import json

from django.conf import settings
from django.contrib.auth.models import User


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
