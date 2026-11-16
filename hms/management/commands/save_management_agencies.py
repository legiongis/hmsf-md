from django.core.management.base import BaseCommand

from hms.models import ManagementAgency


class Command(BaseCommand):
    help = "save all ManagementAgencies"

    def handle(self, *args, **options):

        for m in ManagementAgency.objects.all():
            m.save()
