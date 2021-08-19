import logging
import functools
from django.http import Http404
from django.core.exceptions import PermissionDenied
from arches.app.models.models import ResourceInstance

from hms.utils import user_can_access_resource
from fpan.search.components.site_filter import SiteFilter
from fpan.utils.permission_backend import user_is_old_landmanager

logger = logging.getLogger(__name__)

def user_can_access_resource_instance(function):
    @functools.wraps(function)
    def wrapper(request, *args, **kwargs):

        resourceid = kwargs["resourceid"] if "resourceid" in kwargs else None
        if resourceid is None:
            raise Http404

        if user_can_access_resource(request.user, resourceid):
            return function(request, *args, **kwargs)
        else:
            raise Http404

    return wrapper

def can_access_site_or_report(function):
    @functools.wraps(function)
    def wrapper(request, *args, **kwargs):

        resourceid = kwargs.get("resourceid")
        if resourceid is None:
            raise Http404

        # kick back to old function for old land managers for now
        if user_is_old_landmanager(request.user):
            logger.debug("can_access_site_or_report: processing old land manager")
            if user_can_access_resource(request.user, resourceid):
                return function(request, *args, **kwargs)
            else:
                raise Http404

        graphid = str(ResourceInstance.objects.get(pk=resourceid).graph_id)
        allowed = False

        graph_rules = SiteFilter().compile_rules(request.user, graph=graphid)

        if graph_rules["access_level"] == "full_access":
            allowed = True
        elif graph_rules["access_level"] == "no_access":
            allowed = False
        else:
            resids = SiteFilter().get_resource_list_from_es_query(graph_rules, graphid)
            allowed = resourceid in resids

        if allowed:
            return function(request, *args, **kwargs)
        else:
            raise Http404

    return wrapper