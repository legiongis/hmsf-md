from django.core.management.base import BaseCommand, CommandError
from arches.app.models.models import Node
from arches.app.models.tile import Tile
from arches.app.models.concept import Concept as NonORMConcept

RESOURCE_TO_USE = "f1575fda-6983-4a77-a016-5021dab7697d"

class Command(BaseCommand):

    help = 'bulk addition of user accounts from a csv file'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):

        self.update_tiles()

    def update_tiles(self):
        '''this function looks in all file tiles and updates the url from the old,
        local storage path to the new, S3 path.
        '''

        nodes = Node.objects.filter(datatype="file-list")
        s3url = "https://fpanhms-media.s3.amazonaws.com"

        for n in nodes:
          tiles = Tile.objects.filter(nodegroup_id=n.nodegroup_id)
          for i, t in enumerate(tiles):
            for k, v in t.data.items():
              if isinstance(v, list) and len(v) > 0:
                for f in v:
                  if "/files/uploadedfiles" in f['url']:
                    f['url'] = f['url'].replace("/files/uploadedfiles",s3url)
                    t.save()
                    print i, t.resourceinstance_id
