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

        create_mock_landmanagers()
        create_mock_scout_accounts()
