import os
from django.core import management
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):

    help = 'drops and recreates the app database.'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):

        # import system settings graph and any saved system settings data
        settings_graph = os.path.join(settings.ROOT_DIR, 'db', 'system_settings', 'Arches_System_Settings_Model.json')
        management.call_command("packages", operation="import_graphs", source=settings_graph)

        settings_data = os.path.join(settings.ROOT_DIR, 'db', 'system_settings', 'Arches_System_Settings.json')
        management.call_command("packages", operation="import_business_data", source=settings_data, overwrite=True)

        settings_data_local = os.path.join(settings.APP_ROOT, 'system_settings', 'System_Settings.json')

        if os.path.isfile(settings_data_local):
            management.call_command("packages", operation="import_business_data", source=settings_data_local,
                                    overwrite=True)
