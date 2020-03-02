# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.core import management
from fpan.models import ManagedArea
from fpan.utils.fpan_account_utils import add_fwcc_nicknames


def add_districts(apps, schema_editor):

    management.call_command("add_districts_to_managed_areas")

def remove_wmds(apps, schema_editor):

    ManagedArea.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('fpan', '0012_load_wmd_fixtures'),
    ]

    operations = [
        migrations.RunPython(add_districts)
    ]
