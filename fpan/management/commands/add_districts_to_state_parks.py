import os
import csv
from django.core import management
from django.core.management.base import BaseCommand, CommandError
from arches.app.models.system_settings import settings
from fpan.models.managedarea import ManagedArea

class Command(BaseCommand):

    help = 'collects stats needed for FPAN year-end reporting'

    def add_arguments(self, parser):
        pass
        # parser.add_argument("uuid",help='input the uuid string to find')

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

        mas = ManagedArea.objects.all()

        unmatched = []
        for park, district in lookup.items():
            try:
                obj = ManagedArea.objects.get(name=park)
                obj.sp_district = int(district)
                obj.save()
            except:
                unmatched.append((park, district))
        
        for ma in mas:
            first_word = ma.name.split(" ")[0]
            for un in unmatched:
                if first_word in un[0]:
                    print un, ma.name