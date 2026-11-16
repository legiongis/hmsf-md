from arches.app.models.models import Plugin
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "make some bespoke changes to the default Arches map layers"

    def handle(self, *args, **options):

        etl_manager = Plugin.objects.get(componentname="etl-manager")
        if etl_manager.config:
            etl_manager.config["show"] = True
            etl_manager.save()
        print("config:", etl_manager.config)
