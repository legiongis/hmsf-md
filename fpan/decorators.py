import functools
from django.http import Http404
from django.core.exceptions import PermissionDenied
from arches.app.models.models import ResourceInstance

from hms.utils import user_can_access_resource

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
