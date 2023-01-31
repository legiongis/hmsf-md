# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.core import management

from fpan.decorators import deprecated_migration_operation

@deprecated_migration_operation
def load_wmds(apps, schema_editor):

    management.call_command("loaddata", "watermanagementdistricts.json")

@deprecated_migration_operation
def remove_wmds(apps, schema_editor):

    from fpan.models import ManagedArea
    ManagedArea.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('fpan', '0011_load_region_fixtures'),
    ]

    operations = [
        migrations.RunPython(load_wmds, remove_wmds)
    ]
