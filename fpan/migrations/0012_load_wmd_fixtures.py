# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.core import management
from fpan.models import ManagedArea
from fpan.utils.fpan_account_utils import add_fwcc_nicknames


def load_wmds(apps, schema_editor):

    management.call_command("loaddata", "watermanagementdistricts.json")

    ## these operations add some extra info to some of the managed areas
    ## that is not included in the fixture files.
    #add_fwcc_nicknames()
    #management.call_command('add_districts')

def remove_wmds(apps, schema_editor):

    ManagedArea.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('fpan', '0011_load_region_fixtures'),
    ]

    operations = [
        migrations.RunPython(load_wmds, remove_wmds)
    ]
