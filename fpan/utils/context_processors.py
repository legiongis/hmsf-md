from datetime import datetime
from django.conf import settings
from django.contrib.auth.models import User
from arches.app.models.models import GraphModel
from arches.app.models.system_settings import settings
from arches.app.utils.betterJSONSerializer import JSONSerializer

from hms.models import ManagementArea, ManagementAgency
from .permission_backend import user_is_land_manager, user_is_scout, generate_site_access_html

def make_widget_data():

    all_areas = ManagementArea.objects.all()
    general_areas = all_areas.exclude(category__name="FPAN Region").exclude(category__name="County")
    general_areas = [{
        "id": str(i[0]),
        "selected": "false",
        "text": i[1]
    } for i in general_areas.order_by("display_name").values_list("pk", "display_name") ]

    fpan_regions = [{
        "id": str(i[0]),
        "selected": "false",
        "text": i[1]
    } for i in all_areas.filter(category__name="FPAN Region").values_list("pk", "name") ]

    counties = [{
        "id": str(i[0]),
        "selected": "false",
        "text": i[1]
    } for i in all_areas.filter(category__name="County").values_list("pk", "name") ]

    agencies = [{
        "id": str(i[0]),
        "selected": "false",
        "text": i[1]
    } for i in ManagementAgency.objects.all().values_list("pk", "name") ]

    usernames = [{
        "id": str(i[0]),
        "selected": "false",
        "text": i[1]
    } for i in User.objects.all().order_by("username").values_list("pk", "username")]

    return {
        "lists" : {
            "usernames": usernames,
            "generalAreas": general_areas,
            "fpanRegions": fpan_regions,
            "managementAgencies": agencies,
            "counties": counties,
        }
    }

def widget_data(request):

    # only collect this information for a few specific views
    widget_views = ["resource", "graph_designer", "report", "add-resource"]
    if any([True for i in widget_views if i in request.path.split("/")]):
        return make_widget_data()
    else:
        return { 'lists': {} }

def user_type(request):

    user_type = "anonymous"
    if request.user.is_superuser:
        user_type = "admin"
    elif user_is_land_manager(request.user):
        user_type = "landmanager"
    elif user_is_scout(request.user):
        user_type = "scout"
    return {
        'user_is_admin': request.user.is_superuser,
        'user_is_state': user_is_land_manager(request.user),
        'user_is_scout': user_is_scout(request.user),
        'user_type': user_type,
        'site_access_html': generate_site_access_html(request.user)
    }

def debug(request):
    return {
        'debug':settings.DEBUG,
        'plausible_site_domain': settings.PLAUSIBLE_SITE_DOMAIN,
    }
