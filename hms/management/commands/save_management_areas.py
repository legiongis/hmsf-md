from django.core.management.base import BaseCommand

from hms.models import ManagementArea


class Command(BaseCommand):
    help = "save all ManagementAgencies"

    def handle(self, *args, **options):

        for m in ManagementArea.objects.all():
            m.save()
