import logging

from arches.app.datatypes.datatypes import DomainListDataType
from arches.app.models.models import Widget

from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

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

    def get_option_text(self, node, option_id):

        try:
            return User.objects.get(pk=option_id).username
        except User.DoesNotExist:
            logger.warn(f"index error: user {option_id} not found")
            return "<user not found>"

    def transform_export_values(self, value, *args, **kwargs):

        if value != None:
            try:
                return User.objects.get(pk=value).username
            except User.DoesNotExist:
                logger.warn(f"index error: user {option_id} not found")
                return "<user not found>"

    def validate(self, values, **kwargs):

        return []
