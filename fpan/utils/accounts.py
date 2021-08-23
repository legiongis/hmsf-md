import random
import string
from django.contrib.auth.models import User

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

def generate_password():
    """not currently used, generates an 8-character random password"""
    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8))