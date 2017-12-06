from django.contrib.auth.models import User
from hms.models import Scout

def check_anonymous(user):
    return user.username != 'anonymous'

def check_duplicate_username(newusername):
    chars = ["'", "-", "\"", "_", "."]
    print(newusername)
    for x in chars:
        if x in newusername:
            newusername = newusername.replace(x, "")
    print(newusername)
    inputname = newusername
    inc = 1
    while User.objects.filter(username=newusername).exists():
        if len(inputname) < len(newusername):
            offset = len(newusername) - len(inputname)
            inc = int(newusername[-offset:]) + 1
        newusername = inputname + '{}'.format(inc)
        print(newusername)
    return newusername

def check_state_access(user):
    state_groups = ['FL Aquatic Preserve','FL BAR','FL Forestry','FMSF','FWC','State Park']
    state_user = user.groups.filter(name__in=state_groups).exists()
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
