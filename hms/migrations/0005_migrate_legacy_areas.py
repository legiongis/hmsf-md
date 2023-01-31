from django.db import migrations
from django.core import management

from fpan.decorators import deprecated_migration_operation

@deprecated_migration_operation
def migrate_areas(apps, schema_editor):
    management.call_command("areas", "migrate-legacy-areas", "--quiet")

@deprecated_migration_operation
def remove_areas(apps, schema_editor):
    """manual removal of all the objects that are created in the above command"""

    from hms.models import (
        ManagementArea,
        ManagementAreaGroup,
        ManagementAreaCategory,
        ManagementAgency,
    )
    ManagementAreaGroup.objects.get(name="SP District 1").delete()
    ManagementAreaGroup.objects.get(name="SP District 2").delete()
    ManagementAreaGroup.objects.get(name="SP District 3").delete()
    ManagementAreaGroup.objects.get(name="SP District 4").delete()
    ManagementAreaGroup.objects.get(name="SP District 5").delete()

    ManagementAreaGroup.objects.get(name="Water Management District - North").delete()
    ManagementAreaGroup.objects.get(name="Water Management District - North Central").delete()
    ManagementAreaGroup.objects.get(name="Water Management District - South").delete()
    ManagementAreaGroup.objects.get(name="Water Management District - Southwest").delete()
    ManagementAreaGroup.objects.get(name="Water Management District - South Central").delete()
    ManagementAreaGroup.objects.get(name="Water Management District - West").delete()

    ManagementAreaCategory.objects.get(name="State Park").delete()
    ManagementAgency.objects.get(name="Florida State Parks", code="FSP").delete()
    ManagementAreaCategory.objects.get(name="State Forest").delete()
    ManagementAgency.objects.get(name="Florida Forest Service", code="FFS").delete()
    ManagementAreaCategory.objects.get(name="Aquatic Preserve").delete()
    ManagementAgency.objects.get(name="Florida Coastal Office", code="FCO").delete()
    ManagementAreaCategory.objects.get(name="Fish and Wildlife Conservation Commission").delete()
    ManagementAgency.objects.get(name="Fish and Wildlife Conservation Commission", code="FWCC").delete()
    ManagementAreaCategory.objects.get(name="Conservation Area").delete()
    ManagementAgency.objects.get(name="Office of Water Policy", code="OWP").delete()

    ManagementArea.objects.filter(load_id__startswith="legacy_migration__").delete()


class Migration(migrations.Migration):

    dependencies = [
        ('hms', '0007_managementarea_display_name'),
    ]

    operations = [
        migrations.RunPython(migrate_areas, remove_areas)
    ]
