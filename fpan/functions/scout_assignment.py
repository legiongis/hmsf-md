from django.contrib.auth.models import User

from arches.app.functions.base import BaseFunction
from arches.app.models.resource import Resource

from hms.utils import update_hms_permissions_table


details = {
    'functionid':'4a1da8f0-dddd-11e7-a700-94659cf754d0',
    'name': 'Scout Assignment',
    'type': 'node',
    'description': 'performs some actions whenever a new scout is assigned to a site',
    'defaultconfig': {"assignment_node_id":""},
    'classname': 'ScoutAssignment',
    'component': 'views/components/functions/scout_assignment'
}

class ScoutAssignment(BaseFunction):

    # def get_user_and_resource(self, tile, request):
    #
    #     node_id = self.config['assignment_node_id']
    #     username = tile.data[node_id]
    #     try:
    #         user = User.objects.get(username=username)
    #     except User.DoesNotExist:
    #         user = None
    #
    #     user = request.user
    #     resource = Resource.objects.get(resourceinstanceid=tile.resourceinstance_id)
    #
    #     return (user, resource)


    def save(self,tile,request):
        # u, r = self.get_user_and_resource(tile, request)
        # UserXResourceInstanceAccess.objects.get_or_create(user=u, resource=r)
        update_hms_permissions_table(user=request.user)

    def post_save(self, tile, request):
        raise NotImplementedError

    def on_import(self, tile, request):
        raise NotImplementedError

    def get(self, tile, request):
        raise NotImplementedError

    def delete(self, tile, request):

        # u, r = self.get_user_and_resource(tile, request)
        # UserXResourceInstanceAccess.objects.get(user=u, resource=r).delete()
        update_hms_permissions_table(user=request.user)
