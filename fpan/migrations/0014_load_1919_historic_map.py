# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.core import management

from fpan.decorators import deprecated_migration_operation

@deprecated_migration_operation
def load_1919_historic_map(apps, schema_editor):

    management.call_command("loaddata", "1919-coastal-map.json")

@deprecated_migration_operation
def remove_1919_historic_map(apps, schema_editor):

    from arches.app.models.models import MapSource, MapLayer
    MapLayer.objects.get(name="Inside Route - Key West to New Orleans | 1919").delete()
    MapSource.objects.get(name="coastal-route-map-1919").delete()

class Migration(migrations.Migration):

    dependencies = [
        ('fpan', '0013_add_districts_to_managed_areas'),
    ]

    operations = [
        migrations.RunPython(load_1919_historic_map, remove_1919_historic_map)
    ]
