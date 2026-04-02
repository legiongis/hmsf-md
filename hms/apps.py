from __future__ import unicode_literals

from django.apps import AppConfig


class HmsConfig(AppConfig):
    name = "hms"
    verbose_name = "HMS"

    def ready(self):
        from . import signals  # noqa: F401
