import six
import random
import string
import logging
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator

logger = logging.getLogger(__name__)


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):

    def _make_hash_value(self, user, timestamp):
        return (six.text_type(user.pk) 
                + six.text_type(timestamp)) + six.text_type(user.is_active)

account_activation_token = AccountActivationTokenGenerator()

def check_duplicate_username(newusername):
    chars = ["'", "-", "\"", "_", ".", " "]
    for x in chars:
        if x in newusername:
            newusername = newusername.replace(x, "")
    inputname = newusername
    inc = 1
    while User.objects.filter(username=newusername).exists():
        if len(inputname) < len(newusername):
            offset = len(newusername) - len(inputname)
            inc = int(newusername[-offset:]) + 1
        newusername = inputname + '{}'.format(inc)
    return newusername

def generate_username(firstname, middleinitial, lastname, overwrite=False):
    """combines the first name, middle initial, and last name into a username,
    if overwrite=False (default) a number will be added if a user with this
    name already exists."""

    name = f"{firstname[0].lower()}{middleinitial.lower()}{lastname.lower()}"
    if overwrite is False:
        name = check_duplicate_username(name)

    logger.debug(f"username created: {firstname} {middleinitial} {lastname} --> {name} | overwrite: {overwrite}")
    return name

def generate_password():
    """not currently used, generates an 8-character random password"""
    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8))