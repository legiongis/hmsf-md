import logging

def user_is_land_manager(user):
    return hasattr(user, "landmanager")

def user_is_scout(user):
    return hasattr(user, "scout")
