import os
import csv
import random
import string
from django.conf import settings
from django.contrib.auth.models import User, Group
from arches.app.models.resource import Resource
from hms.models import Scout
from fpan.models import ManagedArea

STATE_GROUP_NAMES = ['FMSF','FL_BAR','FWC','FL_Forestry','FL_AquaticPreserve','StatePark']

def check_anonymous(user):
    return user.username == 'anonymous'

def check_state_access(user):
    state_user = user.groups.filter(name__in=STATE_GROUP_NAMES).exists()
    if user.is_superuser:
        state_user = True
    return state_user

def check_scout_access(user):
    try:
        scout = user.scout
        is_scout = True
    except Scout.DoesNotExist:
        is_scout = False
    return is_scout

