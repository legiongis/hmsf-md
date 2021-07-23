from django.db import migrations
from django.core import management

from hms.models import ManagementArea

def load_extra_management_areas(apps, schema_editor):

    management.call_command("loaddata", "management_areas_july2021")
    for ma in ManagementArea.objects.filter(load_id="extra_management_areas_Jul2021"):
        ma.save()

def remove_extra_management_areas(apps, schema_editor):

    ManagementArea.objects.filter(load_id="extra_management_areas_Jul2021").delete()

class Migration(migrations.Migration):

    dependencies = [
        ('hms', '0005_migrate_legacy_areas'),
    ]

    operations = [
        migrations.RunPython(load_extra_management_areas, remove_extra_management_areas)
    ]
