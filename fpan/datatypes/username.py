from arches.app.datatypes.datatypes import DomainListDataType
from arches.app.models.models import Widget

from django.contrib.auth.models import User

widget = Widget.objects.get(name='username-widget')

details = {
    'widgetid': '99998980-cbd9-11e7-b225-aaaa9c555555',
    'datatype': 'username-datatype',
    'iconclass': 'fa fa-file-code-o',
    'modulename': 'username.py',
    'classname': 'UsernameDataType',
    'defaultwidget': widget,
    'defaultconfig': None,
    'configcomponent': None,
    'configname': None,
    'isgeometric': False
    }

class UsernameDataType(DomainListDataType):

    def get_dropdown_options(self):

        return [{
            "id": str(i.pk),
            "selected": "false",
            "text": i.username
        } for i in User.objects.all() ]

    def get_option_text(self, node, option_id):

        return User.objects.get(pk=option_id).username

    def transform_export_values(self, value, *args, **kwargs):

        if value != None:
            return User.objects.get(pk=value).username

    def validate(self, values, row_number=None, source="", node=None, nodeid=None):

        return []
