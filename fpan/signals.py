import logging

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from arches.app.models.tile import Tile

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Tile)
def join_management_areas_to_resourceinstance(sender, instance, created, **kwargs):
    from .utils import SpatialJoin

    if instance.nodegroup_id in settings.SPATIAL_COORDINATES_NODEGROUPS_IDS:

        logger.debug(f"run spatial join on resource: {instance.resourceinstance_id}")
        try:
            joiner = SpatialJoin()
            joiner.update_resource(instance.resourceinstance)
        except Exception as e:
            logger.error(f"error encoutered: {e}")
