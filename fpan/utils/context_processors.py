from django.conf import settings
from arches.app.models.models import GraphModel
from arches.app.models.system_settings import settings
from arches.app.utils.betterJSONSerializer import JSONSerializer

from .permission_backend import check_state_access, user_is_scout

def user_type(request):

    return {
        'user_is_state': check_state_access(request.user),
        'user_is_scout': user_is_scout(request.user),
        'user_is_admin': request.user.is_superuser,
    }

def debug(request):
    return {
        'debug':settings.DEBUG,
    }
