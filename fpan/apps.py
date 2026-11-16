
from arches.settings_utils import generate_frontend_configuration
from django.apps import AppConfig
from django.conf import settings


class FpanConfig(AppConfig):
    name = "fpan"
    is_arches_application = True

    def ready(self):
        from . import signals  # noqa: F401

        if settings.APP_NAME.lower() == self.name:
            generate_frontend_configuration()
