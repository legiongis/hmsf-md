import time
import logging
import functools
from django.http import Http404
from django.conf import settings
from django.core.exceptions import PermissionDenied
from arches.app.models.models import ResourceInstance
from arches.app.models.resource import Resource

from fpan.search.components.rule_filter import RuleFilter
from fpan.utils.permission_backend import user_is_land_manager

logger = logging.getLogger(__name__)

def can_access_site_or_report(function):
    @functools.wraps(function)
    def wrapper(request, *args, **kwargs):

        start = time.time()

        resourceid = kwargs.get("resourceid")
        if resourceid is None:
            raise Http404

        graphid = str(ResourceInstance.objects.get(pk=resourceid).graph_id)
        allowed = False

        rule = RuleFilter().compile_rules(request.user, graphids=[graphid], single=True)

        if rule.type == "full_access":
            allowed = True
        elif rule.type == "no_access":
            allowed = False
        else:
            resids = RuleFilter().get_resources_from_rule(rule, ids_only=True)
            allowed = resourceid in resids

        logger.debug(f"can_access_site_or_report {allowed}: {time.time()-start}")
        if allowed:
            return function(request, *args, **kwargs)
        else:
            raise Http404

    return wrapper

def can_edit_scout_report(function):
    @functools.wraps(function)
    def wrapper(request, *args, **kwargs):

        resourceid = kwargs.get("resourceid")
        if resourceid is None:
            raise Http404

        allowed = True
        if ResourceInstance.objects.get(pk=resourceid).graph.name == "Scout Report":
            if request.user.is_superuser:
                allowed = True
            elif user_is_land_manager(request.user) and request.user.landmanager.site_access_mode == "FULL":
                allowed = True
            else:
                res = Resource.objects.get(pk=resourceid)
                allowed = str(request.user.pk) in res.get_node_values("Scout ID(s)")

        logger.debug(f"can_edit_scout_report = {allowed}")
        if allowed:
            return function(request, *args, **kwargs)
        else:
            raise Http404

    return wrapper

def deprecated_migration_operation(func):
    def wrapper(*args, **kwargs):
        if settings.DEPRECATE_LEGACY_FIXTURE_LOAD:
            print(settings.DEPRECATE_LEGACY_FIXTURE_LOAD_MSG, end="")
        else:
            func(*args, **kwargs)
    return wrapper
