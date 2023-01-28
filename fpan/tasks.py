from __future__ import absolute_import, unicode_literals
from celery import shared_task

@shared_task
def run_fmsf_import_as_task(loadid, resource_type, truncate=None, dry_run=False, description="", only_extra_ids=False):
    from fpan.etl_modules.fmsf_importer import FMSFImporter
    importer = FMSFImporter(loadid=loadid)
    importer.run_sequence(
        resource_type,
        truncate=truncate,
        dry_run=dry_run,
        description=description,
        only_extra_ids=only_extra_ids,
    )

@shared_task
def run_managed_area_import_as_task(loadid, truncate):
    from fpan.etl_modules.managed_area_importer import ManagedAreaImporter
    importer = ManagedAreaImporter(loadid=loadid)
    importer.run_sequence(truncate)
