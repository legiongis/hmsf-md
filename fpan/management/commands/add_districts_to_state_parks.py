import os
import csv
from django.core.management.base import BaseCommand, CommandError
from fpan.models.managedarea import ManagedArea

class Command(BaseCommand):

    help = 'adds the district number to state parks based on a pre-made csv lookup'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):

        # load the single exported new Scout Report resource and get information from it
        refdatadir = os.path.join("fpan", "management", "commands", "refdata")

        lookup = {}
        lookupfile = os.path.join(refdatadir, "FSP_Districts.csv")
        with open(lookupfile, "r") as f:
            reader = csv.reader(f)
            reader.next()
            for row in reader:
                lookup[row[0]] = row[1]

        unmatched = []
        sps = ManagedArea.objects.filter(category="State Park")
        for sp in sps:
            try:
                sp.sp_district = int(lookup[sp.name])
                sp.save()
            except KeyError:
                print("Invalid park name: {}".format(sp.name))
