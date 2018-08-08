import os
import csv
import string
import random
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group

class Command(BaseCommand):

    help = 'bulk addition of user accounts from a csv file'

    def add_arguments(self, parser):
        parser.add_argument("csv_file",help='path to the csv holding the names of the accounts to add')

    def handle(self, *args, **options):

        self.add_accounts(options['csv_file'])

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
        