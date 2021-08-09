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
            if hasattr(u, "landmanager"):
                if overwrite is True:
                    u.landmanager.delete()
                else:
                    continue
            p = LandManager.objects.create(user=u)

            if u.groups.filter(name="FL_BAR").exists():
                self.set_full_access(p)

            elif u.groups.filter(name="FMSF").exists():
                self.set_full_access(p)

            elif u.groups.filter(name="FL_AquaticPreserve").exists():
                self.set_agency_filter(p, "FCO")

            elif u.username == "SPAdmin":
                self.set_agency_filter(p, "FSP")

            elif u.username == "SFAdmin":
                self.set_agency_filter(p, "FFS")
            
            elif u.username.startswith("SPDistrict"):
                m = ManagementAreaGroup.objects.get(name=f"SP District {u.username[-1]}")
                p.apply_area_filter = True
                p.save()
                p.grouped_areas.add(m)

                self.matched.append((p.user.username, "grouped area = " + m.name))
            
            elif u.username.startswith("SJRWMD"):

                p.apply_area_filter = True
                p.save()

                wmd_n = ManagementAreaGroup.objects.get(name="Water Management District - North")
                wmd_nc = ManagementAreaGroup.objects.get(name="Water Management District - North Central")
                wmd_s = ManagementAreaGroup.objects.get(name="Water Management District - South")
                wmd_sw = ManagementAreaGroup.objects.get(name="Water Management District - Southwest")
                wmd_sc = ManagementAreaGroup.objects.get(name="Water Management District - South Central")
                wmd_w = ManagementAreaGroup.objects.get(name="Water Management District - West")

                if u.username == "SJRWMD":
                    p.grouped_areas.add(wmd_n) 
                    p.grouped_areas.add(wmd_nc)
                    p.grouped_areas.add(wmd_s)
                    p.grouped_areas.add(wmd_sw)
                    p.grouped_areas.add(wmd_sc)
                    p.grouped_areas.add(wmd_w)
                    self.matched.append((p.user.username, "grouped area = all WMD districts"))
                elif u.username == "SJRWMD_NorthRegion" or u.username == "SJRWMD_North":
                    p.grouped_areas.add(wmd_n)
                    self.matched.append((p.user.username, "grouped area = " + wmd_n.name))
                elif u.username == "SJRWMD_NorthCentral":
                    p.grouped_areas.add(wmd_nc)
                    self.matched.append((p.user.username, "grouped area = " + wmd_nc.name))
                elif u.username == "SJRWMD_West":
                    p.grouped_areas.add(wmd_w)
                    self.matched.append((p.user.username, "grouped area = " + wmd_w.name))
                elif u.username == "SJRWMD_South" or u.username == "SJRWMD_SouthRegion":
                    p.grouped_areas.add(wmd_s)
                    self.matched.append((p.user.username, "grouped area = " + wmd_s.name))
                elif u.username == "SJRWMD_Southwest":
                    p.grouped_areas.add(wmd_sw)
                    self.matched.append((p.user.username, "grouped area = " + wmd_sw.name))
                elif u.username == "SJRWMD_SouthCentral":
                    p.grouped_areas.add(wmd_sc)
                    self.matched.append((p.user.username, "grouped area = " + wmd_sc.name))

            else:
                try:
                    # if there is a single area matching this username,
                    # assume area permissions with that single area.
                    m = ManagementArea.objects.get(nickname=u.username)
                    p.apply_area_filter = True
                    p.save()
                    p.individual_areas.add(m)

                    self.matched.append((p.user.username, "area = " + m.name))

                except ManagementArea.DoesNotExist:
                    self.unmatched.append(p.user.username)

    def set_agency_filter(self, profile, agency_code):

        profile.agency = ManagementAgency.objects.get(pk=agency_code)
        profile.apply_agency_filter = True
        profile.save()

        self.matched.append((profile.user.username, "agency = " + agency_code))

    def set_full_access(self, profile):

        profile.full_access = True
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