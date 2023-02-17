# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.core import management

from fpan.decorators import deprecated_migration_operation

@deprecated_migration_operation
def load_slr_layers(apps, schema_editor):

    management.call_command("loaddata", "slr1-layer")
    management.call_command("loaddata", "slr2-layer")
    management.call_command("loaddata", "slr3-layer")
    management.call_command("loaddata", "slr6-layer")
    management.call_command("loaddata", "slr10-layer")

@deprecated_migration_operation
def remove_slr_layers(apps, schema_editor):

    from arches.app.models.models import MapSource, MapLayer
    MapLayer.objects.get(name="1ft Sea Level Rise Inundation (NOAA)").delete()
    MapSource.objects.get(name="slr1-layer").delete()
    
    MapLayer.objects.get(name="2ft Sea Level Rise Inundation (NOAA)").delete()
    MapSource.objects.get(name="slr2-layer").delete()
    
    MapLayer.objects.get(name="3ft Sea Level Rise Inundation (NOAA)").delete()
    MapSource.objects.get(name="slr3-layer").delete()
    
    MapLayer.objects.get(name="6ft Sea Level Rise Inundation (NOAA)").delete()
    MapSource.objects.get(name="slr6-layer").delete()
    
    MapLayer.objects.get(name="10ft Sea Level Rise Inundation (NOAA)").delete()
    MapSource.objects.get(name="slr10-layer").delete()

class Migration(migrations.Migration):

    dependencies = [
        ('fpan', '0014_load_1919_historic_map'),
    ]

    operations = [
        migrations.RunPython(load_slr_layers, remove_slr_layers)
    ]
