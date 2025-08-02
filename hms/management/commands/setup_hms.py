import os
import subprocess
from pathlib import Path

from django.conf import settings
from django.core import management
from django.core.management.base import BaseCommand, CommandError

from arches.app.models.models import MapLayer

from hms.models import ManagementArea, ManagementAgency
from hms.utils import TestUtils

class Command(BaseCommand):

    help = 'creates a set of accounts with various permissions that can be used during testing,'\
        "overwrites set accounts if they already exist."

    def add_arguments(self, parser):
        parser.add_argument("--test-accounts", action="store_true", default=False,
            help='specify whether the mock land manager and scout accounts should be created')
        parser.add_argument("--test-resources", action="store_true", default=False,
            help='specify whether to load a sample set of resource instances')
        parser.add_argument("--use-existing-db", action="store_true", default=False,
            help='use this flag when calling this command during testing, so that the test database is used')

    def handle(self, *args, **options):

        db = settings.DATABASES['default']
        db_name = db['NAME']
        db_user = db['USER']

        if options['use_existing_db'] is not True:
            if not input("\nDrop and recreate the database? y/N ").lower().startswith("y"):
                print("cancelled")
                exit()
            ## replacing the Arches setup_db command here
            # management.call_command('setup_db', force=True)
            print("\033[96m-- Initialize the DATABASE --\033[0m")
            prefix = ["psql", "-U", "postgres"]
            cmd1 = prefix + ["-c", f"DROP DATABASE IF EXISTS {db_name};"]
            subprocess.call(cmd1)
            cmd2 = prefix + ["-c", f"CREATE DATABASE {db_name} WITH OWNER {db_user};"]
            subprocess.call(cmd2)
            cmd3 = prefix + ["-d", db_name, "-c", "CREATE EXTENSION postgis; CREATE EXTENSION \"uuid-ossp\";"]
            subprocess.call(cmd3)

            management.call_command("es", operation="delete_indexes")

            # setup initial Elasticsearch indexes
            management.call_command("es", operation="setup_indexes")

            management.call_command("createcachetable")
            management.call_command("migrate")

            # import system settings graph and any saved system settings data
            settings_graph = Path(settings.APP_ROOT, "system_settings", "Arches_System_Settings_Model.json")
            management.call_command(
                "packages", operation="import_graphs", source=str(settings_graph)
            )

            settings_instance = Path(settings.APP_ROOT, "system_settings", "System_Settings.json")
            management.call_command(
                "packages",
                operation="import_business_data",
                source=str(settings_instance),
                overwrite="overwrite",
            )

        print("\033[96m-- Load Arches PACKAGE --\033[0m")

        management.call_command('packages',
            operation='load_package',
            source=os.path.join(settings.APP_ROOT, 'pkg'),
            yes=True
        )

        print("\033[96m-- Update MAP LAYERS --\033[0m")

        self.update_map_layers()

        print("\033[96m-- Load extra MAP LAYERS --\033[0m")

        management.call_command('loaddata', '1919-coastal-map')
        management.call_command('loaddata', 'slr1-layer')
        management.call_command('loaddata', 'slr2-layer')
        management.call_command('loaddata', 'slr3-layer')
        management.call_command('loaddata', 'slr6-layer')
        management.call_command('loaddata', 'slr10-layer')

        print("\033[96m-- Register SEARCH FILTERS --\033[0m")

        management.call_command('extension', 'register', 'search-filter', source='fpan/search/components/rule_filter.py')
        management.call_command('extension', 'register', 'search-filter', source='fpan/search/components/scout_report_filter.py')

        print("\033[96m-- Load MANAGEMENT AGENCIES --\033[0m")
        management.call_command('loaddata', 'management-agencies')
        print("\033[37mRe-saving all objects to generate RDM concepts...", end="")
        for i in ManagementAgency.objects.all():
            i.save()
        print(" done.\033[0m")

        print("\033[96m-- Load MANAGEMENT AREA CATEGORIES --\033[0m")
        management.call_command('loaddata', 'management-area-categories')

        print("\033[96m-- Load MANAGEMENT AREAS --\033[0m")
        management.call_command('loaddata', 'management-areas-fpan-region')
        management.call_command('loaddata', 'management-areas-state-park')
        management.call_command('loaddata', 'management-areas-state-forest')
        management.call_command('loaddata', 'management-areas-fwcc')
        management.call_command('loaddata', 'management-areas-conservation-area')
        management.call_command('loaddata', 'management-areas-aquatic-preserve')
        management.call_command('loaddata', 'management-areas-hillsborough-co-elapp')
        management.call_command('loaddata', 'management-areas-hillsborough-co-parks')
        management.call_command('loaddata', 'management-areas-july2021')

        print("\033[37mRe-saving all objects to generate display_name and RDM concepts...", end="")
        for i in ManagementArea.objects.all():
            i.save()
        print(" done.\033[0m")

        print("\033[96m-- Load MANAGEMENT AREA GROUPS --\033[0m")
        management.call_command('loaddata', 'management-area-groups')

        print("\033[96m-- Deactivate Default ETL Modules --\033[0m")
        management.call_command(
            "extension", "deactivate", "etl-module",
            name="Import Single CSV",
        )
        management.call_command(
            "extension", "deactivate", "etl-module",
            name="Import Branch Excel",
        )

        print("\033[96m-- Load Site Theme content --\033[0m")
        management.call_command('loaddata', 'site_theme')

        if options['test_accounts']:
            print("\033[96m-- Loading test Scout and Land Manager accounts --\033[0m")
            TestUtils().create_test_scouts()
            TestUtils().create_test_landmanagers()

        if options['test_resources']:
            print("\033[96m-- Loading test resources --\033[0m")
            TestUtils().load_test_resources()
            management.call_command("spatial_join", all=True)

    def update_map_layers(self):

        # rename the default Arches satellite layer
        try:
            l = MapLayer.objects.get(name="satellite")
            l.name = "Satellite"
            l.icon = "fa fa-globe"
            l.save()
        except MapLayer.DoesNotExist:
            pass
        # remove the default Arches streets layer
        try:
            l = MapLayer.objects.get(name="streets")
            l.delete()
        except MapLayer.DoesNotExist:
            pass
        # update the icon for the new HMS basemap
        try:
            l = MapLayer.objects.get(name="HMS Basemap")
            l.icon = "fa fa-stumbleupon"
            l.addtomap = True
            l.save()
        except MapLayer.DoesNotExist:
            pass
