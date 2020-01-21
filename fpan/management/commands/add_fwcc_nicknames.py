from django.core.management.base import BaseCommand, CommandError
from fpan.models import ManagedArea
from fpan.utils.fpan_account_utils import add_fwcc_nicknames

class Command(BaseCommand):

    help = 'special addition of nicknames to FWCC ManagedArea objects'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):

        add_fwcc_nicknames()
