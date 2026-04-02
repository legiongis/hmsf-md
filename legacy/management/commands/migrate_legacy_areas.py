from datetime import datetime
from django.core.management.base import BaseCommand

from fpan.models import ManagedArea, Region
from hms.models import (
    ManagementArea,
    ManagementAgency,
    ManagementAreaGroup,
    ManagementAreaCategory,
)


class Command(BaseCommand):
    help = "Loads Management Areas from shapefile."
    quiet = False

    def add_arguments(self, parser):
        parser.add_argument(
            "operation",
            choices=[
                "load",
                "remove",
                "load-ids",
                "migrate-legacy-areas",
                "make-views",
                "refresh-views",
                "drop-views",
            ],
            help="Specify the operation to carry out.",
        )
        parser.add_argument(
            "-s",
            "--source",
            help="Spatial dataset containing new Management Areas.",
        )
        parser.add_argument(
            "--load-id",
            help="Load id of Management Areas to remove.",
        )
        parser.add_argument(
            "--group-names",
            nargs="+",
            default=[],
            help="Name of group if all Management Areas are to be added to a "
            "single group.",
        )
        parser.add_argument(
            "--category",
            help="Category of these areas. Allows creation of new category on load. "
            "If operation is make-views, only the view for this category will be made. ",
        )
        parser.add_argument(
            "--level",
            choices=["Federal", "State", "City"],
            help="Management Level for these areas.",
        )
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Suppress output messages.",
        )

    def handle(self, *args, **options):

        time_id = datetime.strftime(datetime.now(), "%m%d%y-%H%M%S")
        load_id = f"legacy_migration__{time_id}"

        regions = Region.objects.all()
        fpan_cat, created = ManagementAreaCategory.objects.get_or_create(
            name="FPAN Region"
        )
        ct = 0
        for r in regions:
            newarea, created = ManagementArea.objects.get_or_create(
                name=f"FPAN {r.name} Region", geom=r.geom, category=fpan_cat
            )
            newarea.load_id = load_id
            newarea.save()
            ct += 1

        if not self.quiet:
            print(f"{ct} FPAN regions migrated")

        ## get or create the necessary groups
        sp1 = ManagementAreaGroup.objects.get_or_create(name="SP District 1")[0]
        sp2 = ManagementAreaGroup.objects.get_or_create(name="SP District 2")[0]
        sp3 = ManagementAreaGroup.objects.get_or_create(name="SP District 3")[0]
        sp4 = ManagementAreaGroup.objects.get_or_create(name="SP District 4")[0]
        sp5 = ManagementAreaGroup.objects.get_or_create(name="SP District 5")[0]
        state_groups = {1: sp1, 2: sp2, 3: sp3, 4: sp4, 5: sp5}

        wmd_north = ManagementAreaGroup.objects.get_or_create(
            name="Water Management District - North"
        )[0]
        wmd_northcentral = ManagementAreaGroup.objects.get_or_create(
            name="Water Management District - North Central"
        )[0]
        wmd_south = ManagementAreaGroup.objects.get_or_create(
            name="Water Management District - South"
        )[0]
        wmd_southwest = ManagementAreaGroup.objects.get_or_create(
            name="Water Management District - Southwest"
        )[0]
        wmd_southcentral = ManagementAreaGroup.objects.get_or_create(
            name="Water Management District - South Central"
        )[0]
        wmd_west = ManagementAreaGroup.objects.get_or_create(
            name="Water Management District - West"
        )[0]
        wmd_groups = {
            "North": wmd_north,
            "North Central": wmd_northcentral,
            "South": wmd_south,
            "Southwest": wmd_southwest,
            "South Central": wmd_southcentral,
            "West": wmd_west,
        }

        ct = 0
        for m in ManagedArea.objects.all():
            newarea, created = ManagementArea.objects.get_or_create(
                name=m.name,
                geom=m.geom,
                nickname=m.nickname,
                management_level="State",
            )
            newarea.load_id = load_id
            newarea.save()
            cat = None
            agency = None
            if m.category == "State Park":
                cat, created = ManagementAreaCategory.objects.get_or_create(
                    name="State Park",
                )
                agency, created = ManagementAgency.objects.get_or_create(
                    name="Florida State Parks", code="FSP"
                )
                state_groups[m.sp_district].areas.add(newarea)
            elif m.category == "State Forest":
                cat, created = ManagementAreaCategory.objects.get_or_create(
                    name="State Forest",
                )
                agency, created = ManagementAgency.objects.get_or_create(
                    name="Florida Forest Service", code="FFS"
                )
            elif m.category == "Aquatic Preserve":
                cat, created = ManagementAreaCategory.objects.get_or_create(
                    name="Aquatic Preserve",
                )
                agency, created = ManagementAgency.objects.get_or_create(
                    name="Florida Coastal Office", code="FCO"
                )
            elif m.category == "Fish and Wildlife Conservation Commission":
                cat, created = ManagementAreaCategory.objects.get_or_create(
                    name="Fish and Wildlife Conservation Commission",
                )
                agency, created = ManagementAgency.objects.get_or_create(
                    name="Fish and Wildlife Conservation Commission", code="FWCC"
                )
            elif m.category == "Water Management District":
                cat, created = ManagementAreaCategory.objects.get_or_create(
                    name="Conservation Area",
                )
                agency, created = ManagementAgency.objects.get_or_create(
                    name="Office of Water Policy", code="OWP"
                )
                wmd_groups[m.wmd_district].areas.add(newarea)
            newarea.category = cat
            newarea.management_agency = agency
            newarea.save()
            ct += 1

        if not self.quiet:
            print(f"{ct} Managed Areas migrated")

            print(f"load id: {load_id}")
            print("to undo to this load, run:")
            print(f"\n    python manage.py areas remove --load-id {load_id}\n")
