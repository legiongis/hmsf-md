from arches.app.models.models import MapLayer
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "make some bespoke changes to the default Arches map layers"

    def handle(self, *args, **options):

        # rename the default Arches satellite layer
        try:
            ml = MapLayer.objects.get(name="satellite")
            ml.name = "Satellite"
            ml.icon = "fa fa-globe"
            ml.save()
        except MapLayer.DoesNotExist:
            pass
        # remove the default Arches streets layer
        try:
            ml = MapLayer.objects.get(name="streets")
            ml.delete()
        except MapLayer.DoesNotExist:
            pass
        # update the icon for the new HMS basemap
        try:
            ml = MapLayer.objects.get(name="HMS Basemap")
            ml.icon = "fa fa-stumbleupon"
            ml.addtomap = True
            ml.save()
        except MapLayer.DoesNotExist:
            pass
