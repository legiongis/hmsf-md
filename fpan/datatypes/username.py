import logging

from arches.app.datatypes.datatypes import DomainListDataType
from arches.app.models.models import Widget

from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

widget = Widget.objects.get(name="username-widget")

details = {
    "datatype": "username-datatype",
    "iconclass": "fa fa-file-code-o",
    "modulename": "username.py",
    "classname": "UsernameDataType",
    "defaultwidget": widget,
    "defaultconfig": {"options": []},
    "configcomponent": "views/components/datatypes/domain-value",
    "configname": "domain-value-datatype-config",
    "isgeometric": False,
    "issearchable": True,
}


class UsernameDataType(DomainListDataType):
    def get_option_text(self, node, option_id):
        try:
            option = User.objects.get(pk=option_id).username
        except User.DoesNotExist:
            logger.warning(f"index error: user {option_id} not found")
            option = "<user not found>"
        return {"id": option, "text": option}

    def transform_export_values(self, value, *args, **kwargs):  # pyright: ignore[reportIncompatibleMethodOverride]

        if value is not None:
            try:
                return User.objects.get(pk=value).username
            except User.DoesNotExist:
                logger.warning(f"index error: user {value} not found")
                return f"<user {value} not found>"
        else:
            return "<no user>"

    def validate(self, values, *args, **kwargs):

        return []
