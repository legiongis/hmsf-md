from django.core import management
from django.core.management.base import BaseCommand, CommandError
from fpan.utils.testing import create_mock_landmanagers, create_mock_scout_accounts

class Command(BaseCommand):

    help = 'creates a set of accounts with various permissions that can be used during testing,'\
        "overwrites set accounts if they already exist."

    def add_arguments(self, parser):
        parser.add_argument("--landmanagers", action="store_true", default=False,
            help='specify whether the full complement of state land manager accounts should be created')
        parser.add_argument("--scouts", action="store_true", default=False,
            help='specify whether some mock scout accounts should be created')

    def handle(self, *args, **options):

        print("\033[96m-- Initialize the DATABASE --\033[0m")

        management.call_command('setup_db', force=True)

        print("\033[96m-- Load Arches PACKAGE --\033[0m")

        management.call_command('packages', operation='load_package', source='./pkg', yes=True)

        print("\033[96m-- Load MAP LAYERS --\033[0m")

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

        # create_mock_landmanagers()
        # create_mock_scout_accounts()
