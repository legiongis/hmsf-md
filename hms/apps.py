from __future__ import unicode_literals

from django.apps import AppConfig


class HmsConfig(AppConfig):
    name = 'hms'

    def ready(self):
        from . import signals
