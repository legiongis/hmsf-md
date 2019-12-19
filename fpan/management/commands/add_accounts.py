import os
import csv
import string
import random
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group
from hms.models import Scout, Region
from fpan.utils.fpan_account_creation import load_fpan_state_auth, create_mock_scout_accounts

class Command(BaseCommand):

    help = 'bulk addition of user accounts from a csv file'

    def add_arguments(self, parser):
        parser.add_argument("--csv_file", default=None,
            help='path to the csv holding the names of the accounts to add')
        parser.add_argument("--land_managers", action="store_true", default=False,
            help='specify whether the full complement of state land manager accounts should be created')
        parser.add_argument("--mock_scouts", action="store_true", default=False,
            help='specify whether some mock scout accounts should be created')
        parser.add_argument("--fake_passwords", action="store_true", default=False,
            help='use fake passwords for testing: passwords for state land entities will match the username')

    def handle(self, *args, **options):

        if options['csv_file'] is not None:
            print("not currently supported")
            return

        if options['land_managers'] is True:
            load_fpan_state_auth(options['fake_passwords'])

        if options['mock_scouts'] is True:
            create_mock_scout_accounts()
