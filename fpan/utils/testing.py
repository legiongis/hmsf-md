from django.contrib.auth.models import User, Group
from hms.models import ManagementAgency, LandManager, ManagementArea, Scout
from fpan.models import Region
from .accounts import generate_username

def create_mock_scout(firstname, middleinitial, lastname, pk):

    TEST_PASSWORD = "Testaccount1!"

    username = generate_username(firstname, middleinitial, lastname, overwrite=True)
    s, created = Scout.objects.get_or_create(pk=pk, username=username)
    s.first_name = firstname
    s.last_name = lastname
    s.middle_initial = middleinitial
    s.set_password(TEST_PASSWORD)
    s.save()

    cs_grp = Group.objects.get(name="Crowdsource Editor")
    s.groups.add(cs_grp)

    s.scoutprofile.region_choices.clear()

    return s

def create_mock_scout_accounts():

    print("making Frank D. Hardy: Northeast & Northwest regions, and ASSIGNEDTO=USERNAME permissions")
    s = create_mock_scout("Frank", "D", "Hardy", 5000)
    s.scoutprofile.region_choices.add(Region.objects.get(name="Northwest"))
    s.scoutprofile.region_choices.add(Region.objects.get(name="Northeast"))
    s.scoutprofile.site_interest_type = ["Prehistoric","Historic"]
    s.save()
    print(f"  scout created: {s.username}")

    print("making Joe B. Hardy: Central & East Central regions, and ASSIGNEDTO=USERNAME permissions")
    s = create_mock_scout("Joe", "B", "Hardy", 5001)
    s.scoutprofile.region_choices.add(Region.objects.get(name="Central"))
    s.scoutprofile.region_choices.add(Region.objects.get(name="East Central"))
    s.scoutprofile.site_interest_type = ["Underwater"]
    s.save()
    print(f"  scout created: {s.username}")

    print("making Biff A. Hooper: Southwest & Southeast regions, and ASSIGNEDTO=USERNAME permissions")
    s = create_mock_scout("Biff", "A", "Hooper", 5002)
    s.scoutprofile.region_choices.add(Region.objects.get(name="Southwest"))
    s.scoutprofile.region_choices.add(Region.objects.get(name="Southeast"))
    s.scoutprofile.site_interest_type = ["Prehistoric","Cemeteries"]
    s.save()
    print(f"  scout created: {s.username}")

    print("making Chet J. Morton: Northwest region, and FULL permissions")
    s = create_mock_scout("Chet", "J", "Morton", 5003)
    s.scoutprofile.region_choices.add(Region.objects.get(name="Northwest"))
    s.scoutprofile.site_access_mode = "FULL"
    s.scoutprofile.site_interest_type = ["Prehistoric"]
    s.save()
    print(f"  scout created: {s.username}")

def create_mock_landmanagers():
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
    
    print("making TestMatanzasSF: AGENCY permissions (Florida Forest Service)")
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
