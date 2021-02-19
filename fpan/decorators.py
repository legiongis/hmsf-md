import functools
from django.http import Http404
from django.core.exceptions import PermissionDenied
from arches.app.models.models import ResourceInstance
from fpan.search.components.site_filter import SiteFilter
from hms.models import UserXResourceInstanceAccess


def can_access_resource_instance(function):
    @functools.wraps(function)
    def wrapper(request, *args, **kwargs):

        resourceid = kwargs["resourceid"] if "resourceid" in kwargs else None
        if resourceid is None:
            # technically this should be 403/forbidden
            raise Http404

        try:
            r = ResourceInstance.objects.get(resourceinstanceid=resourceid)
        except ResourceInstance.DoesNotExist:
            raise Http404
        rules = SiteFilter().get_rules(request.user, str(r.graph_id))

        if rules["access_level"] == "full_access":
            can_edit = True
        elif rules["access_level"] == "no_access":
            can_edit = False
        else:
            # this is for land manager 2.0

            if hasattr(request.user, 'landmanager'):
                allowed = UserXResourceInstanceAccess.objects.filter(user=request.user)
                res_ids = [str(i.resource.resourceinstanceid) for i in allowed]
            # retain compatibility for 1.0 for now
            else:
                res_ids = SiteFilter().get_allowed_resource_ids(request.user, str(r.graph_id))["id_list"]
                print(res_ids)
            if resourceid in res_ids:
                can_edit = True
            else:
                can_edit = False

        if can_edit is True:
            return function(request, *args, **kwargs)
        else:
            # technically this should be 403/forbidden
            raise Http404
        return function(request, *args, **kwargs)

    return wrapper
