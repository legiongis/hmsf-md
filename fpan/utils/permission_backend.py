import os
import logging
from arches.app.search.search_engine_factory import SearchEngineFactory
from arches.app.search.elasticsearch_dsl_builder import Query, Bool, Match, Terms, Nested
from arches.app.models.models import Node, ResourceInstance
from hms.models import Scout
from fpan.models import ManagedArea
from arches.app.models.system_settings import settings
try:
    settings.update_from_db()
except:
    pass

logger = logging.getLogger(__name__)

def user_is_anonymous(user):
    return user.username == 'anonymous'


def check_state_access(user):
    state_user = user.groups.filter(name="Land Manager").exists()
    if user.is_superuser:
        state_user = True
    return state_user


def user_is_scout(user):
    try:
        scout = user.scout
        is_scout = True
    except Scout.DoesNotExist:
        is_scout = False
    return is_scout


def user_can_edit_this_resource(user, resourceinstanceid):
    """
    Determines whether this user can edit this specific resource instance.
    Return True or False.
    """

    res = ResourceInstance.objects.get(resourceinstanceid=resourceinstanceid)
    res_access = get_allowed_resource_ids(user, str(res.graph_id))
    if res_access["access_level"] == "full_access":
        return True
    elif res_access["access_level"] == "no_access":
        return False
    else:
        return resourceinstanceid in res_access["id_list"]
