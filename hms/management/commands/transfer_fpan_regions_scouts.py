from django.core.management.base import BaseCommand
from hms.models import ScoutProfile, FPANRegion

class Command(BaseCommand):

    help = 'adds the district number to state parks based on a pre-made csv lookup'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):

        for p in ScoutProfile.objects.all():

            new_regions = FPANRegion.objects.filter(name__in=[i.name for i in p.fpan_regions.all()])
            p.fpan_regions2.set(new_regions)

            print("old:", p.fpan_regions.all())
            print("new:", p.fpan_regions2.all())