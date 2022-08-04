from arches.app.datatypes.datatypes import DomainListDataType
from arches.app.models.models import Widget

from hms.models import ManagementArea, ManagementAgency

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

    def get_option_text(self, node, option_id):

        ## Very Very Very hacky way to reference both ManagementAreas and
        ## ManagementAgencies -- the latter have a pk that is letters.
        ## this should be defined in the datatype configs or something.
        if option_id.isdigit():
            return ManagementArea.objects.get(pk=option_id).__str__()
        else:
            return ManagementAgency.objects.get(pk=option_id).__str__()

    def transform_export_values(self, value, *args, **kwargs):

        if value != None:
            if value.isdigit():
                return ManagementArea.objects.get(pk=value).__str__()
            else:
                return ManagementAgency.objects.get(pk=value).__str__()

    def validate(self, values, **kwargs):

        return []
