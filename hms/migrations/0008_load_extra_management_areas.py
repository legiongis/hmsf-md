from django.db import migrations
from django.core import management

from fpan.decorators import deprecated_migration_operation

@deprecated_migration_operation
def load_extra_management_areas(apps, schema_editor):

    from hms.models import ManagementArea
    management.call_command("loaddata", "management-areas-july2021")
    for ma in ManagementArea.objects.filter(load_id="extra_management_areas_Jul2021"):
        ma.save()

@deprecated_migration_operation
def remove_extra_management_areas(apps, schema_editor):
    from hms.models import ManagementArea
    ManagementArea.objects.filter(load_id="extra_management_areas_Jul2021").delete()

class Migration(migrations.Migration):

    dependencies = [
        ('hms', '0005_migrate_legacy_areas'),
    ]

    operations = [
        migrations.RunPython(load_extra_management_areas, remove_extra_management_areas)
    ]
