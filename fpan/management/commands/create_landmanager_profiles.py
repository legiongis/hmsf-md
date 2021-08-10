from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group
from hms.models import LandManager, ManagementArea, ManagementAgency, ManagementAreaGroup


class Command(BaseCommand):

    help = 'Aug 9th 2021 - command to add LandManager profiles for all existing'\
        'Land Manager accounts (during transition to proper profiles'
    
    matched = []
    unmatched = []

    def add_arguments(self, parser):
        parser.add_argument("--overwrite",
            action="store_true",
        )
        parser.add_argument("--name", "-n")

    def handle(self, *args, **options):

        self.add_profiles(overwrite=options['overwrite'], name=options['name'])

        self.report()

    def add_profiles(self, overwrite=False, name=None):

        users = User.objects.filter(groups__name="Land Manager")
        for u in users:
            if name and u.username != name:
                continue
            p, created = LandManager.objects.get_or_create(user=u)
            if not created and overwrite is False:
                continue

            self.set_agency(p)

            if u.groups.filter(name="FL_BAR").exists():
                self.set_full_access(p)

            elif u.groups.filter(name="FMSF").exists():
                self.set_full_access(p)

            elif u.groups.filter(name="FL_AquaticPreserve").exists():
                self.set_agency_filter(p)

            elif u.username == "SPAdmin":
                self.set_agency_filter(p)

            elif u.username == "SFAdmin":
                self.set_agency_filter(p)

            elif u.username.startswith("SPDistrict"):
                m = ManagementAreaGroup.objects.get(name=f"SP District {u.username[-1]}")
                self.set_area_filter(p, grouped_areas=[m])

            elif u.username.startswith("SJRWMD"):

                wmd_n = ManagementAreaGroup.objects.get(name="Water Management District - North")
                wmd_nc = ManagementAreaGroup.objects.get(name="Water Management District - North Central")
                wmd_s = ManagementAreaGroup.objects.get(name="Water Management District - South")
                wmd_sw = ManagementAreaGroup.objects.get(name="Water Management District - Southwest")
                wmd_sc = ManagementAreaGroup.objects.get(name="Water Management District - South Central")
                wmd_w = ManagementAreaGroup.objects.get(name="Water Management District - West")

                if u.username == "SJRWMD":
                    self.set_area_filter(p, grouped_areas=[wmd_sw, wmd_n, wmd_nc, wmd_s, wmd_sc, wmd_w])
                elif u.username == "SJRWMD_NorthRegion" or u.username == "SJRWMD_North":
                    self.set_area_filter(p, grouped_areas=[wmd_n])
                elif u.username == "SJRWMD_NorthCentral":
                    self.set_area_filter(p, grouped_areas=[wmd_nc])
                elif u.username == "SJRWMD_West":
                    self.set_area_filter(p, grouped_areas=[wmd_w])
                elif u.username == "SJRWMD_South" or u.username == "SJRWMD_SouthRegion":
                    self.set_area_filter(p, grouped_areas=[wmd_s])
                elif u.username == "SJRWMD_Southwest":
                    self.set_area_filter(p, grouped_areas=[wmd_sw])
                elif u.username == "SJRWMD_SouthCentral":
                    self.set_area_filter(p, grouped_areas=[wmd_sc])

            else:
                try:
                    # if there is a single area matching this username,
                    # assume area permissions with that single area.
                    m = ManagementArea.objects.get(nickname=u.username)
                    self.set_area_filter(p, areas=[m])

                except ManagementArea.DoesNotExist:
                    self.unmatched.append(p.user.username)

    def set_agency(self, profile):

        if profile.user.groups.filter(name="FL_AquaticPreserve").exists():
            profile.management_agency_id = "FCO"
        elif profile.user.groups.filter(name="FWC").exists():
            profile.management_agency_id = "FWCC"
        elif profile.user.groups.filter(name="FL_Forestry").exists():
            profile.management_agency_id = "FFS"
        elif profile.user.groups.filter(name="StatePark").exists():
            profile.management_agency_id = "FSP"
        elif profile.user.groups.filter(name="FL_WMD").exists():
            profile.management_agency_id = "OWP"

        profile.save()

    def set_area_filter(self, profile, areas=[], grouped_areas=[]):

        profile.site_access_mode = "AREA"
        profile.save()

        if len(areas) > 0:
            for area in areas:
                profile.individual_areas.add(area)
            l_str = " | ".join([i.name for i in areas])
            self.matched.append((profile.user.username, "areas = " + l_str))

        if len(grouped_areas) > 0:
            for grouped_area in grouped_areas:
                profile.grouped_areas.add(grouped_area)
            l_str = " | ".join([i.name for i in grouped_areas])
            self.matched.append((profile.user.username, "grouped areas = " + l_str))

        profile.save()

    def set_agency_filter(self, profile):

        profile.site_access_mode = "AGENCY"
        profile.save()
        self.matched.append((profile.user.username, "agency = " + profile.management_agency.pk))

    def set_full_access(self, profile):

        profile.site_access_mode = "FULL"
        profile.save()
        self.matched.append((profile.user.username, "full"))

    def report(self):

        print("MATCHED")
        for i in self.matched:
            print(i)
        print(f"{len(self.matched)} profiles added")
        print("\nUNMATCHED")
        for i in self.unmatched:
            print(i)
        print(f"{len(self.unmatched)} still need profiles")