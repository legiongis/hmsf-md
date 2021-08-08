from datetime import datetime
from django.conf import settings
from django.contrib.auth.models import User
from arches.app.models.models import GraphModel
from arches.app.models.system_settings import settings
from arches.app.utils.betterJSONSerializer import JSONSerializer


from hms.models import ManagementArea

try:
    from fpan.datatypes.management_area import ManagementAreaDataType
    from fpan.datatypes.username import UsernameDataType
except ImportError:
    pass

from .permission_backend import user_is_land_manager, user_is_scout

def widget_data(request):

    widget_views = ["resource", "graph_designer", "report", "add-resource"]

    if any([True for i in widget_views if i in request.path.split("/")]):

        try:
            users = UsernameDataType().get_dropdown_options()
            management_areas = ManagementAreaDataType().get_dropdown_options()
            return {
                'lists': {
                    'usernames': users,
                    'managementAreas': management_areas,
                }
            }
        except:
            pass

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
        'user_type': user_type
    }

def debug(request):
    return {
        'debug':settings.DEBUG,
    }
