""" This module holds all of the functions used to create the FPAN accounts,
especially as needed fror development and testing purposes."""

import os
import csv
import json
import random
import string
from django.conf import settings
from django.contrib.auth.models import User, Group
from arches.app.models.resource import Resource
from hms.models import Scout
from fpan.models import ManagedArea, Region


def create_accounts_from_json(json_file):
    '''currently not in use. The idea was to allow the json definition of users
    in a package, and then load them with this command. However, in the case of
    HMS, this action is not needed as the default user accounts are all handled
    in other creation commands below.'''

    with open(json_file,'rb') as configs:
        auth_configs = json.load(configs)

    print "\nclearing all existing users\n----------------------"
    keep_users = ["admin","anonymous"]
    all_users = User.objects.exclude(username__in=keep_users)
    for u in all_users:
        print "  removing user: "+u.username
        u.delete()
    print "    done"
    
    print "\ncreating new Scouts for HMS\n----------------------"
    for group,users in auth_configs.iteritems():
        newgroup = Group.objects.get_or_create(name=group)[0]
        for user,info in users.iteritems():
            print "  creating user:",user
            if group == "Scout":
                newuser = Scout.objects.create_user(user,"",info['password'])
                newuser.first_name = info['first_name']
                newuser.last_name = info['last_name']
                newuser.middle_initial = info['middle_initial']
                newuser.scoutprofile.site_interest_type = info['site_interests']
                for region in info['regions']:
                    print region
                    obj = Region.objects.get(name=region)
                    newuser.scoutprofile.region_choices.add(obj)
                cs_grp = Group.objects.get_or_create(name="Crowdsource Editor")[0]
                newuser.groups.add(cs_grp)
            else:
                newuser = User.objects.create_user(user,"",info['password'])
                newuser.first_name = info['first_name']
                newuser.last_name = info['last_name']
            newuser.save()


def create_mock_scout_accounts():

    print "----------------"
    scout_grp = Group.objects.get_or_create(name="Scout")[0]
    scouts = Scout.objects.all()
    print "deleting existing scouts:",scouts
    for s in scouts:
        s.delete()

    print "creating new scouts:"
    cen_region = Region.objects.get(name="Central")
    ec_region = Region.objects.get(name="East Central")
    ne_region = Region.objects.get(name="Northeast")
    nw_region = Region.objects.get(name="Northwest")
    sw_region = Region.objects.get(name="Southwest")
    se_region = Region.objects.get(name="Southeast")

    ## make a few scouts for testing
    frank = Scout.objects.create_user("fdhardy","","frank")
    frank.first_name = "Frank"
    frank.last_name = "Hardy"
    frank.middle_initial = "D"
    frank.scoutprofile.region_choices.add(cen_region)
    frank.scoutprofile.region_choices.add(ec_region)
    frank.scoutprofile.site_interest_type = ["Prehistoric","Historic"]
    frank.save()
    print "  scout created: Frank Hardy"

    joe = Scout.objects.create_user("jbhardy","","joe")
    joe.first_name = "Joe"
    joe.last_name = "Hardy"
    joe.middle_initial = "B"
    joe.scoutprofile.region_choices.add(ne_region)
    joe.scoutprofile.site_interest_type = ["Cemeteries"]
    joe.save()
    print "  scout created: Joe Hardy"

    chet = Scout.objects.create_user("cjmorton","","chet")
    chet.first_name = "Chet"
    chet.last_name = "Morton"
    chet.middle_initial = "J"
    chet.scoutprofile.region_choices.add(cen_region)
    chet.scoutprofile.region_choices.add(nw_region)
    chet.scoutprofile.site_interest_type = ["Historic"]
    chet.save()
    print "  scout created: Chet Morton"

    biff = Scout.objects.create_user("bahooper","","biff")
    biff.first_name = "Biff"
    biff.last_name = "Hooper"
    biff.middle_initial = "A"
    biff.scoutprofile.region_choices.add(sw_region)
    biff.scoutprofile.region_choices.add(se_region)
    biff.scoutprofile.region_choices.add(ec_region)
    biff.scoutprofile.site_interest_type = ["Historic","Cemeteries","Prehistoric"]
    biff.save()
    print "  scout created: Biff Hooper"

    ## add to the Scout group and Heritage Manager group
    cs_grp = Group.objects.get_or_create(name="Crowdsource Editor")[0]
    for scout in Scout.objects.all():
        scout.groups.add(cs_grp)
        scout.groups.add(scout_grp)


def create_single_account_and_group(agency_name, fake_passwords):

    print("making group: " + agency_name)
    group = Group.objects.get_or_create(name=agency_name)[0]
    print("  new group added " + agency_name)

    pw = generate_password()
    if fake_passwords:
        pw = agency_name

    user = User.objects.get_or_create(username=agency_name)[0]
    user.set_password(pw)
    user.groups.add(group)
    user.save()

    print("  1 user added to group")

    return (user, pw)

def generate_password():

    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8))


def load_fpan_state_auth(fake_passwords=False):
    """builds the groups and users for the state land manager side of things.
    If mock=True, passwords will be the same as the usernames. Otherwise,
    password are randomly generated and stored in a separate log.
    """

    created_users = []

    print "\ncreating one login per group for some state agencies\n----------------------"

    one_offs = ['FL_BAR','FMSF']

    for agency_name in one_offs:

        new_account = create_single_account_and_group(agency_name, fake_passwords)
        created_users.append(new_account)

    print "\ncreating one login per unit and one group for other state agencies\n----------------------"
    
    logins_per_unit_dict = {
        "FL Dept. of Environmental Protection, Div. of Recreation and Parks":"StatePark",
        "FL Dept. of Environmental Protection, Florida Coastal Office":"FL_AquaticPreserve",
        "FL Dept. of Agriculture and Consumer Services, Florida Forest Service":"FL_Forestry",
        "FL Fish and Wildlife Conservation Commission":"FWC",
    }
    
    all = ManagedArea.objects.all()
    for a in logins_per_unit_dict.keys():
            
        lookup = logins_per_unit_dict[a]
        print "making group:",lookup
        group = Group.objects.get_or_create(name=lookup)[0]
        a_ma = all.filter(agency=a)
        
        ct = 0
        for ma in a_ma:
            name = ma.nickname
            pw = generate_password()
            if fake_passwords:
                pw = ma.nickname
            user = User.objects.get_or_create(username=name)[0]
            user.set_password(pw)
            user.save()
            user.groups.add(group)
            user.save()
            created_users.append((user,pw))
            ct+=1
        print "  {} users added to group".format(ct)

    sp_grp = Group.objects.get_or_create(name="StatePark")[0]
    for n in range(1,6):
        name = "SPDistrict"+str(n)
        pw = generate_password()
        if fake_passwords:
            pw = name
        user = User.objects.get_or_create(username=name)[0]
        user.set_password(pw)
        user.save()
        user.groups.add(sp_grp)
        user.save()
        created_users.append((user,pw))
        print("user created: "+name)

    user = User.objects.get_or_create(username="SPAdmin")[0]
    pw = generate_password()
    if fake_passwords:
        pw = name
    user.set_password(pw)
    user.save()
    user.groups.add(sp_grp)
    user.save()
    created_users.append((user,pw))
    print("user created: "+name)

    user = User.objects.get_or_create(username="SFAdmin")[0]
    pw = generate_password()
    if fake_passwords:
        pw = name
    user.set_password(pw)
    user.save()
    sf_grp = Group.objects.get_or_create(name="FL_Forestry")[0]
    user.groups.add(sf_grp)
    user.save()
    created_users.append((user,pw))
    print("user created: "+name)

    ## add all new users to the Crowdsource Editor group and Land Manager group
    cs_grp = Group.objects.get_or_create(name="Crowdsource Editor")[0]
    lm_grp = Group.objects.get_or_create(name="Land Manager")[0]
    for user_pw in created_users:
        user_pw[0].groups.add(cs_grp)
        user_pw[0].groups.add(lm_grp)
        user_pw[0].save()

    with open(os.path.join(settings.SECRET_LOG,"initial_user_info.csv"),"wb") as outcsv:
        write = csv.writer(outcsv)
        write.writerow(("username","password"))
        for user_pw in created_users:
            write.writerow((user_pw[0].username, user_pw[1]))


def create_accounts_from_csv(csv_file):
    """ this function needs to be updated before it is used. it was created
    for a one-off effort, but could be reused if it's fixed up a bit."""

    print "adding accounts"
    outrows = []
    print len(User.objects.all())
    with open(csv_file,"rU") as opencsv:

        reader = csv.reader(opencsv)
        reader.next()

        for row in reader:
            name = row[2]
            pw = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8))
            if len(User.objects.filter(username=name)) > 0:
                print " ",name, "already exists"
                continue
            user = User.objects.create_user(name,"",pw)
            cs_grp = Group.objects.get(name="Crowdsource Editor")
            user.groups.add(cs_grp)
            fwc_grp = Group.objects.get(name="FWC")
            user.groups.add(fwc_grp)
            user.save()
            print " ",user.username, "added"
            outrows.append([name,pw])

    outlog = os.path.join(os.path.dirname(csv_file),os.path.basename(csv_file).replace(".csv","_log.csv"))

    print len(User.objects.all())
    with open(outlog, "wb") as outcsv:
        writer = csv.writer(outcsv)
        writer.writerow(['username','password'])
        for row in outrows:
            writer.writerow(row)


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
    
    ## note 8/1/18
    ## when creating individual accounts for fwcc units, more nickname handling was done in
    ## excel. This is now accounted for in fpan_account_utils.add_fwcc_nicknames()
    
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
