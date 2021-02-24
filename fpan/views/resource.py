from django.utils.decorators import method_decorator
from arches.app.views.resource import (
    ResourceListView,
    ResourceEditLogView,
    ResourceData,
    ResourceTiles,
    ResourceCards,
    ResourceReportView,
    RelatedResourcesView,
)
from arches.app.utils.decorators import (
    can_edit_resource_instance,
    can_read_resource_instance,
)
# from fpan.decorators import can_access_resource_instance
from fpan.decorators import user_can_access_resource_instance


@method_decorator(user_can_access_resource_instance, name="dispatch")
@method_decorator(can_edit_resource_instance, name="dispatch")
class FPANResourceListView(ResourceListView):
    pass


@method_decorator(user_can_access_resource_instance, name="dispatch")
@method_decorator(can_edit_resource_instance, name="dispatch")
class FPANResourceEditLogView(ResourceEditLogView):
    pass


@method_decorator(user_can_access_resource_instance, name="dispatch")
@method_decorator(can_edit_resource_instance, name="dispatch")
class FPANResourceData(ResourceData):
    pass


@method_decorator(user_can_access_resource_instance, name="dispatch")
@method_decorator(can_read_resource_instance, name="dispatch")
class FPANResourceTiles(ResourceTiles):
    pass


@method_decorator(user_can_access_resource_instance, name="dispatch")
@method_decorator(can_read_resource_instance, name="dispatch")
class FPANResourceCards(ResourceCards):
    pass


@method_decorator(user_can_access_resource_instance, name="dispatch")
@method_decorator(can_read_resource_instance, name="dispatch")
class FPANResourceReportView(ResourceReportView):
    pass


@method_decorator(user_can_access_resource_instance, name="dispatch")
@method_decorator(can_read_resource_instance, name="dispatch")
class FPANRelatedResourcesView(RelatedResourcesView):
    pass
