import os
import csv
import json
from datetime import datetime
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group
from hms.models import LandManager, ManagementArea, ManagementAgency, ManagementAreaGroup


class Command(BaseCommand):

    help = 'Aug 9th 2021 - command to add LandManager profiles for all existing'\
        'Land Manager accounts (during transition to proper LM profiles)'

    matched = []
    unmatched = []

    def add_arguments(self, parser):
        parser.add_argument("--overwrite",
            action="store_true",
        )
        parser.add_argument("--name", "-n")

    def handle(self, *args, **options):

        # load the single exported new Scout Report resource and get information from it
        refdatadir = os.path.join("fpan", "management", "commands", "refdata")
        info_file = os.path.join(refdatadir, "profile_migration_lists-Aug2021.json")
        data = {}
        if os.path.isfile(info_file):
            with open(info_file, "r") as op:
                data = json.loads(op.read())

        self.known_missing_areas = data.get('known_missing_areas', [])
        self.special_cases = data.get('special_cases', {})
        self.agency_accounts = data.get('agency_accounts', [])
        self.deactivate_accounts = data.get('deactivate_accounts', {})

        self.add_profiles(overwrite=options['overwrite'], name=options['name'])

        self.report()

    def add_profiles(self, overwrite=False, name=None):

        mock_nicknames = {}
        for i in ManagementArea.objects.all():
            mock_nicknames[self.attempt_nickname(i.name)] = i

        users = User.objects.filter(groups__name="Land Manager")
        for u in users:

            if name is not None and u.username != name:
                continue

            # skip this one user specifically who should just be a scout
            if u.username == "bpburger":
                self.matched.append((u.username, "", "", "not LM so no profile made"))
                continue

            # set this specific user to inactive and don't create a profile for it
            if u.username in self.deactivate_accounts:
                u.is_active = False
                u.save()
                note = self.deactivate_accounts[u.username]
                self.matched.append((u.username, "deactivated", "", note))
                continue

            p, created = LandManager.objects.get_or_create(user=u)
            if not created and overwrite is False:
                continue

            self.set_agency(p)

            # for those whose areas are known missing create profiles to which an area will be added later
            if u.username in self.known_missing_areas:
                self.set_area_filter(p, no_area=True)
                continue
            
            elif u.username in self.agency_accounts:
                self.set_agency_filter(p)

            elif u.groups.filter(name="FL_BAR").exists():
                self.set_full_access(p)

            elif u.groups.filter(name="FMSF").exists():
                self.set_full_access(p)

            elif u.groups.filter(name="FL_AquaticPreserve").exists():
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

                if u.username == "SJRWMD_Admin":
                    self.set_area_filter(p, grouped_areas=[wmd_sw, wmd_n, wmd_nc, wmd_s, wmd_sc, wmd_w])
                elif u.username == "SJRWMD_NorthRegion":
                    self.set_area_filter(p, grouped_areas=[wmd_n, wmd_nc, wmd_w])
                elif u.username == "SJRWMD_SouthRegion":
                    self.set_area_filter(p, grouped_areas=[wmd_s, wmd_sw, wmd_sc])
                elif u.username == "SJRWMD_North":
                    self.set_area_filter(p, grouped_areas=[wmd_n])
                elif u.username == "SJRWMD_NorthCentral":
                    self.set_area_filter(p, grouped_areas=[wmd_nc])
                elif u.username == "SJRWMD_West":
                    self.set_area_filter(p, grouped_areas=[wmd_w])
                elif u.username == "SJRWMD_South":
                    self.set_area_filter(p, grouped_areas=[wmd_s])
                elif u.username == "SJRWMD_Southwest":
                    self.set_area_filter(p, grouped_areas=[wmd_sw])
                elif u.username == "SJRWMD_SouthCentral":
                    self.set_area_filter(p, grouped_areas=[wmd_sc])
                else:
                    self.unmatched.append(p.user.username)

            else:
                try:
                    # if there is a single area matching this username,
                    # assume area permissions with that single area.
                    m = ManagementArea.objects.get(nickname=u.username)
                    self.set_area_filter(p, areas=[m])

                except ManagementArea.DoesNotExist:
                    # final attempt to match with errant nicknames
                    if u.username in mock_nicknames:
                        self.set_area_filter(p, areas=[mock_nicknames[u.username]])
                    elif u.username in self.special_cases:
                        a = ManagementArea.objects.get(nickname=self.special_cases[u.username])
                        self.set_area_filter(p, areas=[a])
                    else:
                        self.unmatched.append(p.user.username)

    def attempt_nickname(self, name):

        abbreviations = [
            ("HistoricStatePark", "HSP"),
            ("StateForestandPark", "SFP"),
            ("StateForest", "SF"),
            ("StatePark", "SP"),
            ("StateTrail", "ST"),
            ("NationalEstuarineResearchReserve", "NERR"),
            ("AgriculturalandConservationEasement", "ACE"),
            ("Wildlife Management Area", "WMA"),
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
        ]

        strip_chars = [" ",".","#","-","'"]
        name = "".join([i for i in name if not i in strip_chars])

        for o, a in abbreviations:
            if o in name:
                name = name.replace(o, a)

        return name

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

    def set_area_filter(self, profile, areas=[], grouped_areas=[], no_area=False):

        profile.site_access_mode = "AREA"
        profile.save()

        if no_area:
            self.matched.append((profile.user.username, "area", "<no area>", "known missing area"))

        if len(areas) > 0:
            for area in areas:
                profile.individual_areas.add(area)
            l_str = " | ".join([i.name for i in areas])
            self.matched.append((profile.user.username, "area", l_str, ""))

        if len(grouped_areas) > 0:
            for grouped_area in grouped_areas:
                profile.grouped_areas.add(grouped_area)
            l_str = " | ".join([i.name for i in grouped_areas])
            self.matched.append((profile.user.username, "area (group)", l_str, ""))

        profile.save()

    def set_agency_filter(self, profile):

        profile.site_access_mode = "AGENCY"
        profile.save()
        self.matched.append((profile.user.username, "agency", profile.management_agency.pk, ""))

    def set_full_access(self, profile):

        profile.site_access_mode = "FULL"
        profile.save()
        self.matched.append((profile.user.username, "full", "", ""))

    def report(self):

        print("MATCHED")
        self.matched.sort()
        for i in self.matched:
            print(i)
        print(f"{len(self.matched)} profiles added")
        print("\nUNMATCHED")
        self.unmatched.sort()
        for i in self.unmatched:
            print(i)
        print(f"{len(self.unmatched)} still need profiles")
        
        d = datetime.now().strftime("%m%d%Y")
        filename = f"lm_account_migration-{d}.csv"
        filepath = os.path.join(settings.LOG_DIR, filename)
        with open(filepath, "w") as op:
            w = csv.writer(op)
            w.writerow(("username", "status/access", "criterion", "note"))
            w.writerows(self.matched)