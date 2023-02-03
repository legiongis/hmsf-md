import os
from django.conf import settings
from django.core import management
from django.core.management.base import BaseCommand, CommandError

from arches.app.models.models import MapLayer

from hms.utils import TestUtils

class Command(BaseCommand):

    help = 'creates a set of accounts with various permissions that can be used during testing,'\
        "overwrites set accounts if they already exist."

    def add_arguments(self, parser):
        parser.add_argument("--test-accounts", action="store_true", default=False,
            help='specify whether the mock land manager and scout accounts should be created')
        parser.add_argument("--use-existing-db", action="store_true", default=False,
            help='use this flag when calling this command during tested, so that the test database is used')

    def handle(self, *args, **options):

        if options['use_existing_db'] is not True:
            print("\033[96m-- Initialize the DATABASE --\033[0m")
            management.call_command('setup_db', force=True)

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

        print("\033[96m-- Load MANAGEMENT AREA GROUPS --\033[0m")
        management.call_command('loaddata', 'management-area-groups')

        if options['test_accounts']:
            TestUtils().create_test_scouts()
            TestUtils().create_test_landmanagers()

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
