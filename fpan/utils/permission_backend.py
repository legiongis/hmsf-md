import os
import logging
from arches.app.search.search_engine_factory import SearchEngineFactory
from arches.app.search.elasticsearch_dsl_builder import Query, Bool, Match, Terms, Nested
from arches.app.models.models import Node, ResourceInstance

from arches.app.models.system_settings import settings
try:
    settings.update_from_db()
except:
    pass

logger = logging.getLogger(__name__)

def user_is_anonymous(user):
    return user.username == 'anonymous'

def user_is_old_landmanager(user):
    return user.groups.filter(name="Land Manager").exists()

def user_is_new_landmanager(user):
    return hasattr(user, "landmanager")

def user_is_land_manager(user):
    return any([user_is_old_landmanager(user), user_is_new_landmanager(user)])

def user_is_scout(user):
    return hasattr(user, "scout")
