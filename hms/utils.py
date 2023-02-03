import os
import six
import json
import random
import string
import logging
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.test import Client
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from hms.forms import ScoutForm
from hms.models import ManagementAgency, LandManager, ManagementArea, Scout

logger = logging.getLogger(__name__)


TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "tests", "data")

class TestUtils():

    def create_test_scouts(self):
        """ This function can be called from test cases or from anywhere in
        the app. """

        with open(os.path.join(TEST_DATA_DIR, "test_scouts.json"), "r") as o:
            scouts = json.load(o)
        for s in scouts:
            self.create_scout_from_json(s)

    def create_scout_from_json(self, scout_data):
        """ This function takes a json object and feeds it into the
        Scout creation form, creating a new Scout and profile. Then
        the activation token is used to activate the account."""

        form = ScoutForm(data=scout_data)
        if not form.is_valid():
            raise Exception(form.errors)

        scout, uidb64, token = create_scout_from_valid_form(form)
        assert len(Scout.objects.filter(username=scout.username)) == 1
        assert scout.is_active is False

        c = Client()
        c.get(f"/activate/?uidb64={uidb64}&token={token}")
        scout.refresh_from_db()
        assert scout.is_active is True

        return scout

    def create_test_landmanagers(self):
        """create a few land managers to demo different permissions levels"""

        TEST_PASSWORD = "Testaccount1!"

        print("making TestMatanzasSF: AREA permissions (Matanzas State Forest)")
        u, created = User.objects.get_or_create(pk=5004, username="TestMatanzasSF")
        u.set_password(TEST_PASSWORD)
        u.save()
        p, created = LandManager.objects.get_or_create(user=u)
        p.management_agency = ManagementAgency.objects.get(code="FFS")
        p.site_access_mode = "AREA"
        p.save()
        p.individual_areas.add(ManagementArea.objects.get(name="Matanzas State Forest"))
        print(f"  land manager created: {u.username}")
        
        print("making TestAdminSF: AGENCY permissions (Florida Forest Service)")
        u, created = User.objects.get_or_create(pk=5005, username="TestAdminSF")
        u.set_password(TEST_PASSWORD)
        u.save()
        p, created = LandManager.objects.get_or_create(user=u)
        p.management_agency = ManagementAgency.objects.get(code="FFS")
        p.site_access_mode = "AGENCY"
        p.save()
        print(f"  land manager created: {u.username}")

        print("making TestFaverDykesSP: AREA permissions (Faver-Dykes State Park)")
        u, created = User.objects.get_or_create(pk=5006, username="TestFaverDykesSP")
        u.set_password(TEST_PASSWORD)
        u.save()
        p, created = LandManager.objects.get_or_create(user=u)
        p.management_agency = ManagementAgency.objects.get(code="FSP")
        p.site_access_mode = "AREA"
        p.save()
        p.individual_areas.add(ManagementArea.objects.get(name="Faver-Dykes State Park"))
        print(f"  land manager created: {u.username}")

        print("making TestFPANOffice: permissions set to FULL")
        u, created = User.objects.get_or_create(pk=5007, username="TestFPANOffice")
        u.set_password(TEST_PASSWORD)
        u.save()
        p, created = LandManager.objects.get_or_create(user=u)
        p.site_access_mode = "FULL"
        p.save()
        print(f"  land manager created: {u.username}")

        print("making TestBanishedLM: permissions set to NONE)")
        u, created = User.objects.get_or_create(pk=5008, username="TestBanishedLM")
        u.set_password(TEST_PASSWORD)
        u.save()
        p, created = LandManager.objects.get_or_create(user=u)
        p.site_access_mode = "NONE"
        p.save()
        print(f"  land manager created: {u.username}")


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
