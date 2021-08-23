import os
import csv
from django.conf import settings
from fpan.models import ManagedArea


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
