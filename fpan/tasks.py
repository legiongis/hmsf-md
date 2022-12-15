from __future__ import absolute_import, unicode_literals
from celery import shared_task

@shared_task
def run_fmsf_import_as_task(loadid, truncate):
    from fpan.etl_modules.fmsf_importer import FMSFImporter
    importer = FMSFImporter(loadid=loadid)
    importer.run_sequence(truncate)

@shared_task
def run_managed_area_import_as_task(loadid, truncate):
    from fpan.etl_modules.managed_area_importer import ManagedAreaImporter
    importer = ManagedAreaImporter(loadid=loadid)
    importer.run_sequence(truncate)
