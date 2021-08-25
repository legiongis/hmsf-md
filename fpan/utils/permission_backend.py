import logging

logger = logging.getLogger(__name__)

def user_is_anonymous(user):
    return user.username == 'anonymous'

def user_is_land_manager(user):
    return hasattr(user, "landmanager")

def user_is_scout(user):
    return hasattr(user, "scout")
