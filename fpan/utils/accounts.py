from django.conf import settings
from django.contrib.auth.models import User, Group
from arches.app.models.resource import Resource
from arches.app.models.models import Node, GraphModel
from arches.app.utils.betterJSONSerializer import JSONSerializer, JSONDeserializer
from arches.app.search.elasticsearch_dsl_builder import Bool, Match, Query, Nested, Term, Terms, GeoShape, Range, MinAgg, MaxAgg, RangeAgg, Aggregation, GeoHashGridAgg, GeoBoundsAgg, FiltersAgg, NestedAgg
from fpan.search.elasticsearch_dsl_builder import Type
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
        print state_group_name

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
        elif state_group_name == "FWC":
            term_filter['value'] = 'FL Fish and Wildlife Conservation Commission'
        else:
            print state_group_name + " not handled properly"
            
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
    
    ## note 8/1/18
    ## when creating individual accounts for fwcc units, more nickname handling was done in
    ## excel. This is not accounted for here, so if this function is ever updated to accommodate
    ## fwcc, a close look must be taken at those new unit names.
    
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
    rv_grp = Group.objects.get_or_create(name="Resource Reviewer")[0]
    
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

def add_doc_specific_criterion(dsl,spec_type,all_types,criterion={}):

    ## if there is no criterion to add, return original dsl
    if not criterion:
        return dsl
    print "adding criterion:"
    print criterion

    paramount = Bool()
    for doc_type in all_types:

        ## add special string filter for specified node in type
        if doc_type == spec_type:

            ## if no_access is the permission level for the user, exclude doc
            if criterion == 'no_access':
                paramount.must_not(Type(type=doc_type))
                continue

            node = Node.objects.filter(graph_id=spec_type,name=criterion['node_name'])
            if len(node) == 1:
                nodegroup = str(node[0].nodegroup_id)
            else:
                nodegroup = ""
                print "error finding specified node '{}', criterion ignored".format(criterion['node_name'])
                return dsl

            new_string_filter = Bool()
            new_string_filter.must(Match(field='strings.string', query=criterion['value'], type='phrase'))
            new_string_filter.filter(Terms(field='strings.nodegroup_id', terms=[nodegroup]))
            nested = Nested(path='strings', query=new_string_filter)

            ## manual test to see if any criteria have been added to the query yet
            f = dsl._dsl['query']['bool']['filter']
            m = dsl._dsl['query']['bool']['must']
            mn = dsl._dsl['query']['bool']['must_not']
            s = dsl._dsl['query']['bool']['should']

            ## if they have, then the new statement needs to be MUST
            if f or m or mn or s:
                paramount.must(nested)

            ## otherwise, use SHOULD
            else:
                paramount.should(nested)

        ## add good types
        else:
            paramount.should(Type(type=doc_type))

    dsl.add_query(paramount)

    return dsl

def get_doc_type(request):

    type_filter = request.GET.get('typeFilter', '')
    use_ids = []

    if type_filter != '':
        type_filters = JSONDeserializer().deserialize(type_filter)

        ## add all positive filters to the list of good ids
        pos_filters = [i['graphid'] for i in type_filters if not i['inverted']]
        for pf in pos_filters:
            use_ids.append(pf)

        ## if there are negative filters, make a list of all possible ids and
        ## subtract the negative filter ids from it.
        neg_filters = [i['graphid'] for i in type_filters if i['inverted']]
        if len(neg_filters) > 0:
            all_rm_ids = GraphModel.objects.filter(isresource=True).values_list('graphid', flat=True)
            use_ids = [str(i) for i in all_rm_ids if not str(i) in neg_filters]

    else:
        resource_models = GraphModel.objects.filter(isresource=True).values_list('graphid', flat=True)
        use_ids = [str(i) for i in resource_models]

    if len(use_ids) == 0:
        ret = []
    else:
        ret = list(set(use_ids))
    return ret

def apply_advanced_docs_permissions(dsl, request):

    docs_perms = settings.RESOURCE_MODEL_USER_RESTRICTIONS
    doc_types = get_doc_type(request)
    for doc in doc_types:
        if not doc in docs_perms.keys() or not 'default' in docs_perms[doc].keys():
            print "no ['default'] permissions for this resource model:{}".format(doc)
            continue

        level = docs_perms[doc]['default']['level']
        print level
        if level == "no_access":
            filter = "no_access"
        elif level == "term_filter":
            filter = docs_perms[doc]['default']['term_filter']
        else:
            continue

        filter = get_perm_details(request.user,doc)
        print "filter:", filter
        dsl = add_doc_specific_criterion(dsl,doc,doc_types,criterion=filter)

    return dsl
