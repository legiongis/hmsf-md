import os
import csv
from django.conf import settings
from fpan.models import ManagedArea

## some methods below are still used by old migrations. Refactoring those
## migrations (somehow) could allow for the removal of this file.

def add_fwcc_nicknames():
    """this function is used after all of the fixtures have been loaded
    to add nicknames to the FWC areas, because they are not included in
    the data fixtures."""

    lmus = ManagedArea.objects.filter(category="Fish and Wildlife Conservation Commission")

    abbreviations = (
        ("WildlifeManagementArea", "WMA"),
        ("WaterfowlManagementArea", "WMA"),
        ("WildlifeandEnvironmentalArea", "WEA"),
        ("ConservationBankConservationEasements", "CBCE"),
        ("GopherTortoiseRecipientSites", "GTRS"),
        ("Preserve", "Pres"),
        ("GopherTortoiseRecipientSite", "GTRS"),
        ("ConservationBankConservationEasement", "CBCE"),
        ("ConservationEasement", "CE"),
        ("PublicShootingRange", "PSR"),
        ("JohnCandMarianaJones", "JCandMJ"),
    )

    strip_chars = [" ", ".", "#", "-", "'", "/"]

    for lmu in lmus:
        nickname = lmu.name
        for sc in strip_chars:
            nickname = nickname.replace(sc, "")

        for abbr in abbreviations:
            if abbr[0] in nickname:
                nickname = nickname.replace(abbr[0], abbr[1])
        lmu.nickname = nickname
        try:
            lmu.save()
        except Exception as e:
            print("ERROR saving managed area: {}".format(lmu.name))
            print(e)

def add_state_park_districts():

    lookup = {}
    lookupfile = os.path.join(settings.APP_ROOT, "utils", "reference_data", "FSP_Districts.csv")
    with open(lookupfile, "r") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            lookup[row[0]] = row[1]

    unmatched = []
    sps = ManagedArea.objects.filter(category="State Park")
    for sp in sps:
        try:
            sp.sp_district = int(lookup[sp.name])
            sp.save()
        except KeyError:
            print("Invalid park name: {}".format(sp.name))

def add_water_management_districts():

    lookup = {}
    lookupfile = os.path.join(settings.APP_ROOT, "utils", "reference_data", "WMD_Districts.csv")
    with open(lookupfile, "r") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            lookup[row[0]] = row[1]

    unmatched = []
    wmds = ManagedArea.objects.filter(category="Water Management District")
    for wmd in wmds:
        try:
            wmd.wmd_district = lookup[wmd.name]
            wmd.save()
        except KeyError:
            print("Invalid park name: {}".format(wmd.name))

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
    ## excel. This is now accounted for in add_fwcc_nicknames()

    agencies = [i[0] for i in ManagedArea.objects.order_by().values_list('agency').distinct()]
    d = {}
    join_dict = {}
    for a in agencies:
        lookup = agency_dict[a]
        print(f"{a} {lookup}")
        if a == "FL Fish and Wildlife Conservation Commission":
            continue
        a_ma = all.filter(agency=a)
        print(len(a_ma))
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
                print(sn)
            if len(sn)>30:
                ct+=1
                print(sn)
            join_dict[ma.name] = sn

        print(f"{ct} are too long")
        d[lookup]=ct

    print(len(join_dict))
    names = join_dict.keys()
    names.sort()
    with open(os.path.join(settings.LOG_DIR,"nicknames.csv"),"wb") as csvout:
        writer = csv.writer(csvout)
        writer.writerow(['name','nickname'])
        for n in names:
            writer.writerow([n,join_dict[n]])