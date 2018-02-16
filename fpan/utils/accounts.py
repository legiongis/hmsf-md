from django.conf import settings
from django.contrib.auth.models import User, Group
from arches.app.models.resource import Resource
from hms.models import Scout
from fpan.models import ManagedArea
import random
import string
import os
import csv

STATE_GROUP_NAMES = ['FMSF','FL_BAR','FWC','FL_Forestry','FL_AquaticPreserve','StatePark']

def check_anonymous(user):
    return user.username == 'anonymous'

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
    
def get_perm_details(user,doc_type):

    term_filter = {}

    ## return false for admins to get full access to everything
    if user.is_superuser:
        return False
    
    ## return false if there are no user-based restrictions for this resource model
    if not doc_type in settings.RESOURCE_MODEL_USER_RESTRICTIONS.keys():
        return False
        
    elif check_state_access(user):
    
        ## figure out what state group the user belongs to
        for sg in STATE_GROUP_NAMES:
            if user.groups.filter(name=sg).exists():
                state_group_name = sg
                break

        ## return false for a few of the state agencies that get full access
        if state_group_name in ["FMSF","FL_BAR"]:
            return False
        else:
            term_filter = settings.RESOURCE_MODEL_USER_RESTRICTIONS[doc_type]['State']['term_filter']
        ## get full agency name to match with node value otherwise
        if state_group_name == "StatePark":
            term_filter['value'] = 'FL Dept. of Environmental Protection, Div. of Recreation and Parks'
        elif state_group_name == "FL_AquaticPreserve":
            term_filter['value'] = 'FL Dept. of Environmental Protection, Florida Coastal Office'
        elif state_group_name == "FL_Forestry":
            term_filter['value'] = 'FL Dept. of Agriculture and Consumer Services, Florida Forest Service'
        else:
            print "ERROR, this line should not be reached"
            
    elif check_scout_access(user):
        term_filter = settings.RESOURCE_MODEL_USER_RESTRICTIONS[doc_type]['Scout']['term_filter']
        term_filter['value'] = user.username
        
    elif check_anonymous(user):
        term_filter = settings.RESOURCE_MODEL_USER_RESTRICTIONS[doc_type]['default']['level']

    return term_filter
    
def user_can_edit_resource_instance(user,resourceid=None):
    if not resourceid:
        return True
    res = Resource.objects.get(pk=resourceid)
    perms = get_perm_details(user,str(res.graph.pk))
    if perms:
        if not perms['value'] in res.get_node_values(perms['node_name']):
            return False
    return True

def make_managed_area_nicknames():
    """this is a helper function that was written to make acceptable usernames
    (no spaces or punctuation, and < 30 characters) from the names of Managed 
    Areas. It produces a CSV that is later used to join with a shapefile and 
    create a fixture and load into the ManagedArea.nickname field."""
    all = ManagedArea.objects.all()
    
    agency_dict = {
        "FL Fish and Wildlife Conservation Commission":"FWC",
        "FL Dept. of Environmental Protection, Div. of Recreation and Parks":"StatePark",
        "FL Dept. of Environmental Protection, Florida Coastal Office":"FL_AquaticPreserve",
        "FL Dept. of Agriculture and Consumer Services, Florida Forest Service":"FL_Forestry"
    }
    
    agencies = [i[0] for i in ManagedArea.objects.order_by().values_list('agency').distinct()]
    d = {}
    join_dict = {}
    for a in agencies:
        lookup = agency_dict[a]
        print a, lookup
        if a == "FL Fish and Wildlife Conservation Commission":
            continue
        a_ma = all.filter(agency=a)
        print len(a_ma)
        ct = 0
        abbreviations1 = {
            "Historic State Park":"HSP",
            "State Forest and Park":"SFP"
        }
            
        abbreviations2 = {
            "State Forest":"SF",
            "State Park":"SP",
            "State Trail":"ST",
            "National Estuarine Research Reserve":"NERR",
            "Agricultural and Conservation Easement":"ACE"
        }
        
        strip_chars = [" ",".","#","-","'"]
            
        for ma in a_ma:
            sn = ma.name
            for k,v in abbreviations1.iteritems():
                if k in sn:
                    abbr = v
                sn = sn.replace(k,v)
            for k,v in abbreviations2.iteritems():
                if k in sn:
                    abbr = v
                sn = sn.replace(k,v)
            sn = "".join([i for i in sn if not i in strip_chars])
            if len(sn)>30:
                sn = ma.name.split(" ")[0]+ma.name.split(" ")[1]+abbr
                sn = "".join([i for i in sn if not i in strip_chars])
                print sn
            if len(sn)>30:
                ct+=1
                print sn
            join_dict[ma.name] = sn
            
        print ct,"are too long"
        d[lookup]=ct

    print len(join_dict)
    names = join_dict.keys()
    names.sort()
    with open(os.path.join(settings.SECRET_LOG,"nicknames.csv"),"wb") as csvout:
        writer = csv.writer(csvout)
        writer.writerow(['name','nickname'])
        for n in names:
            writer.writerow([n,join_dict[n]])
     
def load_fpan_state_auth(mock=False):
    """builds the groups and users for the state land manager side of things.
    If mock=True, passwords will be the same as the usernames. Otherwise,
    password are randomly generated and stored in a separate log.
    """
    
    outlist = []
    cs_grp = Group.objects.get_or_create(name="Crowdsource Editor")[0]
    
    print "\ncreating one login per group for some state agencies\n----------------------"
    one_offs = ['FL_BAR','FMSF','FWC']
    
    for agency_name in one_offs:
        
        print "making group:",agency_name
        existing = Group.objects.filter(name=agency_name)
        for e in existing:
            print "  deleting existing group:",agency_name
            e.delete()
        
        pw = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8))
        if mock:
            pw = agency_name
        group = Group.objects.get_or_create(name=agency_name)[0]
        print "  new group added",agency_name
        
        existing_users = User.objects.filter(username=agency_name)
        for e in existing_users:
            e.delete()
            
        user = User.objects.create_user(agency_name,"",pw)
        user.groups.add(group)
        user.groups.add(cs_grp)
        user.save()
        outlist.append((agency_name,pw))
        print "  1 user added to group"
    
    print "\ncreating one login per unit and one group for other state agencies\n----------------------"
    
    logins_per_unit_dict = {
        "FL Dept. of Environmental Protection, Div. of Recreation and Parks":"StatePark",
        "FL Dept. of Environmental Protection, Florida Coastal Office":"FL_AquaticPreserve",
        "FL Dept. of Agriculture and Consumer Services, Florida Forest Service":"FL_Forestry"
    }
    
    all = ManagedArea.objects.all()
    agencies = [i[0] for i in ManagedArea.objects.order_by().values_list('agency').distinct()]
    for a in agencies:
    
        if not a in logins_per_unit_dict.keys():
            continue
            
        lookup = logins_per_unit_dict[a]
        print "making group:",lookup
        group = Group.objects.get_or_create(name=lookup)[0]
        a_ma = all.filter(agency=a)
        
        ct = 0
        for ma in a_ma:
            name = ma.nickname
            pw = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8))
            if mock:
                pw = ma.nickname
            existing_users = User.objects.filter(username=name)
            for e in existing_users:
                e.delete()
            user = User.objects.create_user(name,"",pw)
            user.groups.add(group)
            user.groups.add(cs_grp)
            user.save()
            outlist.append((name,pw))
            ct+=1
        print "  {} users added to group".format(ct)
                
    with open(os.path.join(settings.SECRET_LOG,"initial_user_info.csv"),"wb") as outcsv:
        write = csv.writer(outcsv)
        write.writerow(("username","password"))
        for user_pw in outlist:
            write.writerow(user_pw)
