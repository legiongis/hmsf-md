# Source: https://testdriven.io/courses/django-celery/auto-reload/

import subprocess

from django.core.management.base import BaseCommand
from django.utils import autoreload


def restart_celery():
    subprocess.call(["pkill", "-f", "celery.*worker"])
    subprocess.call(["celery", "-A", "fpan", "worker", "--loglevel=info"])


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("Starting celery worker with autoreload...")
        autoreload.run_with_reloader(restart_celery)
