# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

from fpan.decorators import deprecated_migration_operation

@deprecated_migration_operation
def add_districts(apps, schema_editor):

    from fpan.utils.legacy_utils import (
        add_state_park_districts,
        add_water_management_districts,
    )

    add_state_park_districts()
    add_water_management_districts()

class Migration(migrations.Migration):

    dependencies = [
        ('fpan', '0012_load_wmd_fixtures'),
    ]

    operations = [
        migrations.RunPython(add_districts)
    ]
