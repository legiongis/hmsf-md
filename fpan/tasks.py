from __future__ import absolute_import, unicode_literals
import logging
from celery import shared_task

logger = logging.getLogger(__name__)

@shared_task
def run_sequence_as_task(loadid, resource_type, truncate=None, dry_run=False, description="", only_extra_ids=False):
    from fpan.etl_modules.fmsf_importer import FMSFImporter
    FMSFImporter().run_sequence(
        resource_type,
        loadid=loadid,
        truncate=truncate,
        dry_run=dry_run,
        description=description,
        only_extra_ids=only_extra_ids,
    )

@shared_task
def run_management_area_import_as_task(loadid, ma_group=None, ma_category=None, ma_agency=None, ma_level=None, description=""):
    from fpan.etl_modules.management_area_importer import ManagementAreaImporter
    ManagementAreaImporter().run_sequence(
        loadid=loadid,
        ma_group=ma_group,
        ma_category=ma_category,
        ma_agency=ma_agency,
        ma_level=ma_level,
        description=description,
    )

@shared_task
def run_full_spatial_join():
    from arches.app.models.models import ResourceInstance
    from fpan.utils import SpatialJoin
    joiner = SpatialJoin()

    resource_graphs = ["Archaeological Site", "Historic Cemetery", "Historic Structure"]
    for res in ResourceInstance.objects.filter(graph__name__in=resource_graphs):
        logger.debug(f"spatial join resource: {res.pk}")
        joiner.update_resource(res)