from arches.app.datatypes.datatypes import DomainListDataType
from arches.app.models.models import Widget

from hms.models import ManagementArea

widget = Widget.objects.get(name='management-area-widget')

details = {
    'datatype': 'management-area-datatype',
    'iconclass': 'fa fa-file-code-o',
    'modulename': 'management_area.py',
    'classname': 'ManagementAreaDataType',
    'defaultwidget': widget,
    'defaultconfig': {"options": []},
    'configcomponent': 'views/components/datatypes/domain-value',
    'configname': 'domain-value-datatype-config',
    'isgeometric': False,
    'issearchable': True,
    }

class ManagementAreaDataType(DomainListDataType):

    def get_dropdown_options(self):

        values = ManagementArea.objects.all().values_list("pk", "display_name")
        return [{
            "id": str(i[0]),
            "selected": "false",
            "text": i[1]
        } for i in values ]

    def get_option_text(self, node, option_id):

        return ManagementArea.objects.get(pk=option_id).__str__()

    def transform_export_values(self, value, *args, **kwargs):

        if value != None:
            return ManagementArea.objects.get(pk=value).__str__()

    def validate(self, values, row_number=None, source="", node=None, nodeid=None):

        return []
