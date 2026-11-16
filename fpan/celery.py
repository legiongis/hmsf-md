import os
import platform

from celery import Celery

if platform.system().lower() == "windows":
    os.environ.setdefault("FORKED_BY_MULTIPROCESSING", "1")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fpan.settings")
app = Celery("fpan")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
