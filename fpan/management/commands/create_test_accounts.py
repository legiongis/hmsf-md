import os
import csv
import string
import random
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group
from hms.models import Scout, Region
from fpan.utils.fpan_account_creation import create_mock_landmanagers, create_mock_scout_accounts
from fpan.utils.fpan_account_utils import generate_username

class Command(BaseCommand):

    help = 'creates a set of accounts with various permissions that can be used during testing'

    def add_arguments(self, parser):
        parser.add_argument("--csv_file", default=None,
            help='path to the csv holding the names of the accounts to add')
        parser.add_argument("--landmanagers", action="store_true", default=False,
            help='specify whether the full complement of state land manager accounts should be created')
        parser.add_argument("--scouts", action="store_true", default=False,
            help='specify whether some mock scout accounts should be created')
        parser.add_argument("--fake_passwords", action="store_true", default=False,
            help='use fake passwords for testing: passwords for state land entities will match the username')
        parser.add_argument("--overwrite",
            action="store_true",
            default=False,
            help='remove existing test accounts and recreate them')

    def handle(self, *args, **options):

        if options['csv_file'] is not None:
            print("not currently supported")
            return

        if options['landmanagers'] is True:
            # load_fpan_state_auth(fake_passwords=options['fake_passwords'])
            create_mock_landmanagers()

        if options['scouts'] is True:
            create_mock_scout_accounts()

        
