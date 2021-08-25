from arches.app.functions.base import BaseFunction

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

    def save(self,tile,request):
        pass

    def post_save(self, tile, request):
        raise NotImplementedError

    def on_import(self, tile, request):
        raise NotImplementedError

    def get(self, tile, request):
        raise NotImplementedError

    def delete(self, tile, request):
        pass
