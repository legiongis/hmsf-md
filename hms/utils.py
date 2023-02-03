import six
import random
import string
import logging
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

logger = logging.getLogger(__name__)


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):

    def _make_hash_value(self, user, timestamp):
        return (six.text_type(user.pk) 
                + six.text_type(timestamp)) + six.text_type(user.is_active)

account_activation_token = AccountActivationTokenGenerator()

def create_scout_from_valid_form(form):
    """Takes a validated ScoutForm() and creates a new Scout/ScoutProfile
    from it. Return a tuple with the user and an activation token."""

    firstname = form.cleaned_data.get('first_name')
    middleinitial = form.cleaned_data.get('middle_initial')
    lastname = form.cleaned_data.get('last_name')
    newusername = generate_username(firstname, middleinitial, lastname)
    s = form.save(commit=False)
    s.is_active = False
    s.username = newusername
    s.save()

    # now add some ScoutProfile info from the same form
    s.scoutprofile.fpan_regions.set(form.cleaned_data.get('fpan_regions', []))
    s.scoutprofile.zip_code = form.cleaned_data.get('zip_code')
    s.scoutprofile.background = form.cleaned_data.get('background')
    s.scoutprofile.relevant_experience = form.cleaned_data.get('relevant_experience')
    s.scoutprofile.interest_reason = form.cleaned_data.get('interest_reason')
    s.scoutprofile.site_interest_type = form.cleaned_data.get('site_interest_type')
    s.scoutprofile.save()

    token = account_activation_token.make_token(s)
    encoded_uid = urlsafe_base64_encode(force_bytes(s.pk))

    return(s, encoded_uid, token)

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