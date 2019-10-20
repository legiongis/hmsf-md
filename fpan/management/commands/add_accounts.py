import os
import csv
import string
import random
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group
from hms.models import Scout, Region
from fpan.utils.accounts import load_fpan_state_auth

class Command(BaseCommand):

    help = 'bulk addition of user accounts from a csv file'

    def add_arguments(self, parser):
        parser.add_argument("--csv_file", default=None,
            help='path to the csv holding the names of the accounts to add')
        parser.add_argument("--land_managers", action="store_true", default=False,
            help='specify whether the full complement of state land manager accounts should be created')
        parser.add_argument("--mock_scouts", action="store_true", default=False,
            help='specify whether some mock scout accounts should be created')
        parser.add_argument("--fake_passwords", action="store_true", default=False,
            help='use fake passwords for testing: passwords for state land entities will match the username')

    def handle(self, *args, **options):

        if options['csv_file'] is not None:
            self.add_accounts(options['csv_file'])

        if options['land_managers'] is True:
            self.add_land_manager_accounts(mock=options['fake_passwords'])

        if options['mock_scouts'] is True:
            self.add_mock_scout_accounts()

    def add_accounts(self,csv_file):

        print "adding accounts"
        outrows = []
        print len(User.objects.all())
        with open(csv_file,"rU") as opencsv:

            reader = csv.reader(opencsv)
            reader.next()

            for row in reader:
                name = row[2]
                pw = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8))
                if len(User.objects.filter(username=name)) > 0:
                    print " ",name, "already exists"
                    continue
                user = User.objects.create_user(name,"",pw)
                cs_grp = Group.objects.get(name="Crowdsource Editor")
                user.groups.add(cs_grp)
                fwc_grp = Group.objects.get(name="FWC")
                user.groups.add(fwc_grp)
                user.save()
                print " ",user.username, "added"
                outrows.append([name,pw])

        outlog = os.path.join(os.path.dirname(csv_file),os.path.basename(csv_file).replace(".csv","_log.csv"))

        print len(User.objects.all())
        with open(outlog, "wb") as outcsv:
            writer = csv.writer(outcsv)
            writer.writerow(['username','password'])
            for row in outrows:
                writer.writerow(row)

    def add_land_manager_accounts(self, mock=False):

        load_fpan_state_auth(mock)

    def add_mock_scout_accounts(self):
        print "----------------"
        scout_grp = Group.objects.get_or_create(name="Scout")[0]
        scouts = Scout.objects.all()
        print "deleting existing scouts:",scouts
        for s in scouts:
            s.delete()

        print "creating new scouts:"
        cen_region = Region.objects.get(name="Central")
        ec_region = Region.objects.get(name="East Central")
        ne_region = Region.objects.get(name="Northeast")
        nw_region = Region.objects.get(name="Northwest")
        sw_region = Region.objects.get(name="Southwest")
        se_region = Region.objects.get(name="Southeast")

        ## make a few scouts for testing
        frank = Scout.objects.create_user("fdhardy","","frank")
        frank.first_name = "Frank"
        frank.last_name = "Hardy"
        frank.middle_initial = "D"
        frank.scoutprofile.region_choices.add(cen_region)
        frank.scoutprofile.region_choices.add(ec_region)
        frank.scoutprofile.site_interest_type = ["Prehistoric","Historic"]
        frank.save()
        print "  scout created: Frank Hardy"

        joe = Scout.objects.create_user("jbhardy","","joe")
        joe.first_name = "Joe"
        joe.last_name = "Hardy"
        joe.middle_initial = "B"
        joe.scoutprofile.region_choices.add(ne_region)
        joe.scoutprofile.site_interest_type = ["Cemeteries"]
        joe.save()
        print "  scout created: Joe Hardy"

        chet = Scout.objects.create_user("cjmorton","","chet")
        chet.first_name = "Chet"
        chet.last_name = "Morton"
        chet.middle_initial = "J"
        chet.scoutprofile.region_choices.add(cen_region)
        chet.scoutprofile.region_choices.add(nw_region)
        chet.scoutprofile.site_interest_type = ["Historic"]
        chet.save()
        print "  scout created: Chet Morton"

        biff = Scout.objects.create_user("bahooper","","biff")
        biff.first_name = "Biff"
        biff.last_name = "Hooper"
        biff.middle_initial = "A"
        biff.scoutprofile.region_choices.add(sw_region)
        biff.scoutprofile.region_choices.add(se_region)
        biff.scoutprofile.region_choices.add(ec_region)
        biff.scoutprofile.site_interest_type = ["Historic","Cemeteries","Prehistoric"]
        biff.save()
        print "  scout created: Biff Hooper"

        ## add to the Scout group and Heritage Manager group
        cs_grp = Group.objects.get_or_create(name="Crowdsource Editor")[0]
        for scout in Scout.objects.all():
            scout.groups.add(cs_grp)
            scout.groups.add(scout_grp)
