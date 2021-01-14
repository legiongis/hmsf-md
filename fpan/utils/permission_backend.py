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


def user_is_land_manager(user):

    state_user = False

    if hasattr(user, "landmanager"):
        print("user_is_land_manager: this is a land manager 2.0")
        state_user = True

    elif user.groups.filter(name="Land Manager").exists():
        print("user_is_land_manager: this is a land manager 1.0")
        state_user = True

    ## this should really not be here, but upstream code will need to account
    ## for its removal
    elif user.is_superuser:
        state_user = True

    return state_user


def user_is_scout(user):
    return hasattr(user, "scout")


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
