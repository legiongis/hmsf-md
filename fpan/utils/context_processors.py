from django.conf import settings
from django.contrib.auth.models import User
from arches.app.models.models import GraphModel
from arches.app.models.system_settings import settings
from arches.app.utils.betterJSONSerializer import JSONSerializer

from .permission_backend import user_is_land_manager, user_is_scout

def user_type(request):

    user_type = "anonymous"
    if user_is_scout(request.user):
        user_type = "scout"
    elif user_is_land_manager(request.user):
        user_type = "landmanager"
    elif request.user.is_superuser:
        user_type = "admin"

    users = [{"username": i.username} for i in User.objects.all()]

    return {
        'user_is_state': user_is_land_manager(request.user),
        'user_is_scout': user_is_scout(request.user),
        'user_is_admin': request.user.is_superuser,
        'user_type': user_type,
        'user_list': users
    }

def debug(request):
    return {
        'debug':settings.DEBUG,
    }
