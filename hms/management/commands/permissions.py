from django.core.management.base import BaseCommand, CommandError

from hms.utils import update_hms_permissions_table

class Command(BaseCommand):

    help = 'Loads Management Areas from shapefile.'
    quiet = False

    def add_arguments(self, parser):
        parser.add_argument(
            'operation',
            choices=["update"],
            help="Specify the operation to carry out.",
        )
        parser.add_argument(
            '-u',
            '--user',
            default=None,
            help='Single user for whom permissions should be updated.',
        )
        parser.add_argument(
            '--noinput',
            action="store_true",
            help='Runs without user interaction.',
        )

    def handle(self, *args, **options):

        user = options["user"]
        if options["user"] is not None:
            user = User.objects.get(username=user)

        if options['operation'] == "update":
            update_hms_permissions_table(user=user)
