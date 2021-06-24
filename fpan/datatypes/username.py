from arches.app.datatypes.datatypes import DomainListDataType
from arches.app.models.models import Widget

from django.contrib.auth.models import User

widget = Widget.objects.get(name='username-widget')

details = {
    'datatype': 'username-datatype',
    'iconclass': 'fa fa-file-code-o',
    'modulename': 'username.py',
    'classname': 'UsernameDataType',
    'defaultwidget': widget,
    'defaultconfig': {"options": []},
    'configcomponent': 'views/components/datatypes/domain-value',
    'configname': 'domain-value-datatype-config',
    'isgeometric': False,
    'issearchable': True,
    }

class UsernameDataType(DomainListDataType):

    def get_dropdown_options(self):

        values = User.objects.all().values_list("pk", "username")

        return [{
            "id": str(i[0]),
            "selected": "false",
            "text": i[1]
        } for i in values]

    def get_option_text(self, node, option_id):

        return User.objects.get(pk=option_id).username

    def transform_export_values(self, value, *args, **kwargs):

        if value != None:
            return User.objects.get(pk=value).username

    def validate(self, values, row_number=None, source="", node=None, nodeid=None):

        return []
