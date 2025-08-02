import json
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand

from arches.app.models.models import NodeGroup

class Command(BaseCommand):

    help = 'creates a set of accounts with various permissions that can be used during testing,'\
        "overwrites set accounts if they already exist."

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):

        def prune_nodegroups(data):
            resources = []
            for res in data['business_data']['resources']:
                newtiles = []
                for tile in res['tiles']:
                    if NodeGroup.objects.filter(nodegroupid=tile['nodegroup_id']).exists():
                        newtiles.append(tile)
                res['tiles'] = newtiles
                resources.append(res)
            return {"business_data":{"resources":resources}}

        test_resource_dir = Path(Path(settings.APP_ROOT).parent, "tests", "data", "resources")
        resource_files = [
            Path(test_resource_dir, "test_archaeological_sites.json"),
            Path(test_resource_dir, "test_historic_structures.json"),
            Path(test_resource_dir, "test_cemeteries.json"),
        ]

        for path in resource_files:
            with open(path, "r") as o:
                data = json.load(o)
                pruned = prune_nodegroups(data)
            with open(path, "w") as o:
                json.dump(pruned, o, indent=2)

