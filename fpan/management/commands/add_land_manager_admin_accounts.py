import os
import csv
import string
import random
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group


class Command(BaseCommand):

    help = 'bulk addition of user accounts from a csv file'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):

        self.add_accounts()

    def add_accounts(self):

        cs_grp = Group.objects.get_or_create(name="Crowdsource Editor")[0]
        sf_grp = Group.objects.get_or_create(name="FL_Forestry")[0]
        sp_grp = Group.objects.get_or_create(name="StatePark")[0]
        
        for n in range(1,6):
            name = "SPDistrict"+str(n)
            user = User.objects.get_or_create(username=name)[0]
            user.set_password(name+"_123#")
            user.save()
            user.groups.add(sp_grp)
            user.groups.add(cs_grp)
            user.save()
            print("user created: "+name)

        name = "SPAdmin"
        user = User.objects.get_or_create(username=name)[0]
        user.set_password(name+"_123#")
        user.save()
        user.groups.add(sp_grp)
        user.groups.add(cs_grp)
        user.save()
        print("user created: "+name)
        
        name = "SFAdmin"
        user = User.objects.get_or_create(username=name)[0]
        user.set_password(name+"_123#")
        user.save()
        user.groups.add(sf_grp)
        user.groups.add(cs_grp)
        user.save()
        print("user created: "+name)
