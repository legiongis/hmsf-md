from django.core.management.base import BaseCommand

from hms.utils import TestUtils


class Command(BaseCommand):
    help = "creates a set of accounts and resources for use during development"

    def handle(self, *args, **options):

        TestUtils().create_test_scouts()
        TestUtils().create_test_landmanagers()
        TestUtils().load_test_resources()
