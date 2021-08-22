from django.contrib.auth.models import User
from fpan.models import ManagedArea

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

def generate_username(firstname, middleinitial, lastname, overwrite=False):
    """combines the first name, middle initial, and last name into a username,
    if overwrite=False (default) a number will be added if a user with this
    name already exists."""

    name = f"{firstname[0].lower()}{middleinitial.lower()}{lastname.lower()}"
    if overwrite:
        return name
    else:
        return check_duplicate_username(name)

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