from __future__ import unicode_literals

from django.apps import AppConfig


class FpanConfig(AppConfig):
    name = 'fpan'

    def ready(self):
        from . import signals  # noqa: F401
