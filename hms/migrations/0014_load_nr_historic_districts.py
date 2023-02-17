from django.core import management
from django.db import migrations

from hms.models import ManagementArea, ManagementAreaCategory

def load_districts(apps, schema_editor):
    cat, created = ManagementAreaCategory.objects.get_or_create(name="NR Historic District")
    management.call_command("loaddata", "pen-fb-sa-historic-disctricts.json")
    for nr in ManagementArea.objects.filter(load_id="nr-districts-Sept2022"):
        nr.category = cat
        nr.save()

def remove_districts(apps, schema_editor):
    ManagementArea.objects.filter(load_id="nr-districts-Sept2022").delete()
    ManagementAreaCategory.objects.filter(name="NR Historic District").delete()

class Migration(migrations.Migration):

    dependencies = [
        ('hms', '0013_auto_20220909_1552'),
    ]

    operations = [
        migrations.RunPython(load_districts, remove_districts)
    ]
