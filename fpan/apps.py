from __future__ import unicode_literals

from django.apps import AppConfig
from django.conf import settings

from arches.settings_utils import generate_frontend_configuration


class FpanConfig(AppConfig):
    name = "fpan"
    is_arches_application = True

    def ready(self):
        from . import signals  # noqa: F401

        if settings.APP_NAME.lower() == self.name:
            generate_frontend_configuration()
