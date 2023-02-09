import os
import csv
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from arches.app.models.resource import Resource
from arches.app.models.graph import Graph

class Command(BaseCommand):

    help = 'export all of the FMSF site ids from resources in the database'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
    
        site_models = [
            "Archaeological Site",
            "Historic Cemetery",
            "Historic Structure"
        ]
    
        for g in Graph.objects.all():
            if not g.name in site_models:
                continue

            sites = [i for i in Resource.objects.all() if i.graph_id == g.pk]

            print("{} Count: {}".format(g.name, len(sites)))
            
            fname = "ids-{}.csv".format(g.name.replace(" ",""))
            with open(os.path.join(settings.LOG_DIR, fname), "wb") as out:
                writer = csv.writer(out)
                writer.writerow(["ResourceID","FMSF ID"])
                for s in sites:
                    writer.writerow([s.resourceinstanceid, s.get_node_values("FMSF ID")[0]])
        