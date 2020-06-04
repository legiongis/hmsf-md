from django.core.management.base import BaseCommand, CommandError
from fpan.utils.email import send_weekly_summary

class Command(BaseCommand):

    help = 'collects stats needed for FPAN year-end reporting'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            default=None,
            help='date from which the past week dates will be calculated',
        )

    def handle(self, *args, **options):

        send_weekly_summary(use_date=options['date'])
