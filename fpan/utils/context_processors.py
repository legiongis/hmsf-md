from django.conf import settings
from arches.app.models.models import GraphModel
from arches.app.models.system_settings import settings
from arches.app.utils.betterJSONSerializer import JSONSerializer

from .permission_backend import check_state_access, user_is_scout, get_match_conditions
from .helpers import get_inline_resources


def user_type(request):

    full_access = request.user.is_superuser
    if request.user.groups.filter(name="FL_BAR").exists() or \
       request.user.groups.filter(name="FMSF").exists():
        full_access = True

    return {
        'user_is_state': check_state_access(request.user),
        'user_is_scout': user_is_scout(request.user),
        'user_is_admin': request.user.is_superuser,
        'full_site_access': full_access
    }

def report_info(request):

    if request.resolver_match.url_name == "resource_report":
        resid = request.resolver_match.kwargs['resourceid']
        inlines = get_inline_resources(resid)
        return {"inline_data": inlines}
    else:
        return {}

def debug(request):
    return {
        'debug':settings.DEBUG,
        'testsetting': "yesyesyes"
    }
