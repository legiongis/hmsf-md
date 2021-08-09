import os
import psycopg2
from datetime import datetime
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import MultiPolygon

from hms.models import (
    ManagementArea,
    ManagementAgency,
    ManagementAreaGroup,
    ManagementAreaCategory,
)

class Command(BaseCommand):

    help = 'Loads Management Areas from shapefile.'
    quiet = False

    def add_arguments(self, parser):
        parser.add_argument(
            'operation',
            choices=["load", "remove", "load-ids", "migrate-legacy-areas",
                     "make-views", "refresh-views", "drop-views"],
            help="Specify the operation to carry out.",
        )
        parser.add_argument(
            '-s',
            '--source',
            help='Spatial dataset containing new Management Areas.',
        )
        parser.add_argument(
            '--load-id',
            help='Load id of Management Areas to remove.',
        )
        parser.add_argument(
            '--group-names',
            nargs="+",
            default=[],
            help='Name of group if all Management Areas are to be added to a '
                'single group.',
        )
        parser.add_argument(
            '--category',
            help='Category of these areas. Allows creation of new category on load. '\
                 'If operation is make-views, only the view for this category will be made. ',
        )
        parser.add_argument(
            '--level',
            choices=["Federal", "State", "County", "City"],
            help='Management Level for these areas.',
        )
        parser.add_argument(
            '--quiet',
            action="store_true",
            help='Suppress output messages.',
        )

    def handle(self, *args, **options):

        if options['quiet'] is True:
            self.quiet = True

        if options['operation'] == "load":
            self.load_areas(options['source'],
                            options['group_names'],
                            options['level'],
                            options['category'])
        if options['operation'] == "remove":
            self.remove_areas(options['load_id'])
        if options['operation'] == "load-ids":
            self.list_load_ids()
        if options['operation'] == "migrate-legacy-areas":
            self.migrate_legacy_areas()
        if options['operation'] == "make-views":
            self.make_views(category=options["category"])
        if options['operation'] == "refresh-views":
            self.refresh_views(category=options["category"])
        if options['operation'] == "drop-views":
            self.drop_views(category=options["category"])

    def load_areas(self, source, group_names, level="", category=""):

        # generate load_id from filename and time.
        source_file = os.path.basename(source)
        file_name = os.path.splitext(source_file)[0]
        time_id = datetime.strftime(datetime.now(), "%m%d%y-%H%M%S")
        load_id = f"{file_name}__{time_id}"

        add_to_groups = []
        for group_name in group_names:
            try:
                group = ManagementAreaGroup.objects.get(name=group_name)
                response = input(f"Add to existing group '{group_name}'? Y/n ")
                if response.lower().startswith("n"):
                    exit()
            except ManagementAreaGroup.DoesNotExist:
                response = input(f"Create new group '{group_name}'? Y/n ")
                if response.lower().startswith("n"):
                    exit()
                group = ManagementAreaGroup.objects.create(name=group_name)
            add_to_groups.append(group)

        if category != "":
            if len(ManagementAreaCategory.objects.filter(name=category)) == 0:
                response = input(f"Create new category '{category}'? Y/n ")
                if response.lower().startswith("n"):
                    exit()
                cat = ManagementAreaCategory.objects.create(name=group_name)
            else:
                cat = ManagementAreaCategory.objects.get(name=category)

        # load the source file as an iterable layer. this method performs some
        # data integrity checks as well.
        dataset = self.load_source(source)

        # allow all case combinations for name field. previous check in
        # load_source ensures this won't fail.
        name_field = [i for i in dataset.fields if i.lower() == "name"][0]

        load_ct = 0
        for feature in dataset:
            if feature.geom.geom_type == "Polygon":
                geom = MultiPolygon(feature.geom.geos)
            elif feature.geom.geom_type == "MultiPolygon":
                geom = feature.geom.geos
            else:
                print("skipping invalid geom type: " + feature.geom.geom_type)
            new_ma = ManagementArea.objects.create(
                name=feature.get(name_field),
                geom=geom,
                load_id=load_id,
            )
            if category != "":
                new_ma.category = cat
            if level != "":
                new_ma.management_level = level
            new_ma.save()

            for group in add_to_groups:
                group.areas.add(new_ma)
            load_ct += 1

        print(f"{load_ct} Management Areas loaded.")
        print(f"load id: {load_id}")

        print("recreating materialized views")
        self.make_views()

        print(f"to undo to this load, run:")
        print(f"\n    python manage.py areas remove --load-id {load_id}\n")

    def load_source(self, source):

        try:
            ds = DataSource(source)
            layer = ds[0]
        except Exception as e:
            print("error loading datasource:")
            print(e)
            exit()

        # check for name field
        if not "name" in [i.lower() for i in layer.fields]:
            print("cancelling: no 'name' field present in dataset.")
            exit()

        # check SRID in first feature:
        for feature in layer:
            if feature.geom.srid != 4326:
                print(f"invalid SRID: {feature.geom.srid}.")
                print("cancelling: reproject dataset to EPGS:4326 (WGS84) "
                    "before trying again.")
                exit()
            break

        return layer

    def remove_areas(self, load_id):
        ma = ManagementArea.objects.filter(load_id=load_id)
        if len(ma) == 0:
            print("No Management Areas match this load id.")
            exit()
        response = input(f"Remove {len(ma)} Management Areas? Y/n ")
        if response.lower().startswith("n"):
            exit()
        ma.delete()
    
        print("recreating materialized views")
        self.make_views()

    def list_load_ids(self):

        ids = ManagementArea.objects.all().values("load_id").distinct()
        for id in ids:
            print(id)

    def migrate_legacy_areas(self):

        time_id = datetime.strftime(datetime.now(), "%m%d%y-%H%M%S")
        load_id = f"legacy_migration__{time_id}"

        from fpan.models import ManagedArea, Region

        regions = Region.objects.all()
        fpan_cat, created = ManagementAreaCategory.objects.get_or_create(name="FPAN Region")
        ct = 0
        for r in regions:
            newarea, created = ManagementArea.objects.get_or_create(
                name=f"FPAN {r.name} Region",
                geom=r.geom,
                category = fpan_cat
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
        state_groups = {1: sp1, 2: sp2, 3: sp3, 4:sp4, 5: sp5}

        wmd_north = ManagementAreaGroup.objects.get_or_create(name="Water Management District - North")[0]
        wmd_northcentral = ManagementAreaGroup.objects.get_or_create(name="Water Management District - North Central")[0]
        wmd_south = ManagementAreaGroup.objects.get_or_create(name="Water Management District - South")[0]
        wmd_southwest = ManagementAreaGroup.objects.get_or_create(name="Water Management District - Southwest")[0]
        wmd_southcentral = ManagementAreaGroup.objects.get_or_create(name="Water Management District - South Central")[0]
        wmd_west = ManagementAreaGroup.objects.get_or_create(name="Water Management District - West")[0]
        wmd_groups = {
            "North": wmd_north,
            "North Central": wmd_northcentral,
            "South": wmd_south,
            "Southwest": wmd_southwest,
            "South Central": wmd_southcentral,
            "West": wmd_west
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
            if m.category == "State Park":
                cat, created = ManagementAreaCategory.objects.get_or_create(
                    name="State Park",
                )
                agency, created = ManagementAgency.objects.get_or_create(
                    name="Florida State Parks",
                    code="FSP"
                )
                state_groups[m.sp_district].areas.add(newarea)
            elif m.category == "State Forest":
                cat, created = ManagementAreaCategory.objects.get_or_create(
                    name="State Forest",
                )
                agency, created = ManagementAgency.objects.get_or_create(
                    name="Florida Forest Service",
                    code="FFS"
                )
            elif m.category == "Aquatic Preserve":
                cat, created = ManagementAreaCategory.objects.get_or_create(
                    name="Aquatic Preserve",
                )
                agency, created = ManagementAgency.objects.get_or_create(
                    name="Florida Coastal Office",
                    code="FCO"
                )
            elif m.category == "Fish and Wildlife Conservation Commission":
                cat, created = ManagementAreaCategory.objects.get_or_create(
                    name="Fish and Wildlife Conservation Commission",
                )
                agency, created = ManagementAgency.objects.get_or_create(
                    name="Fish and Wildlife Conservation Commission",
                    code="FWCC"
                )
            elif m.category == "Water Management District":
                cat, created = ManagementAreaCategory.objects.get_or_create(
                    name="Conservation Area",
                )
                agency, created = ManagementAgency.objects.get_or_create(
                    name="Office of Water Policy",
                    code="OWP"
                )
                wmd_groups[m.wmd_district].areas.add(newarea)
            newarea.category = cat
            newarea.management_agency = agency
            newarea.save()
            ct += 1

        if not self.quiet:
            print(f"{ct} Managed Areas migrated")

            print(f"load id: {load_id}")
            print(f"to undo to this load, run:")
            print(f"\n    python manage.py areas remove --load-id {load_id}\n")
    
    def make_hms_viewname(self, basename):

        prefix = "mv_hms"
        name = basename.lower().replace(" ", "_").replace("-", "_")
        view_name = f"{prefix}_{name}"

        return view_name

    def make_views(self, category=""):

        db = settings.DATABASES['default']
        db_conn = "dbname = {} port = {} user = {} host = {} password = {}".format(
            db['NAME'],db['PORT'],db['USER'],db['HOST'],db['PASSWORD'])
        conn = psycopg2.connect(db_conn)

        for cat in ManagementAreaCategory.objects.all():

            if category and cat.name != category:
                continue

            view_name = self.make_hms_viewname(cat.name)

            print(f"category: {cat.name}")
            print(f"creating materialized view {view_name}")
            
            sql = f"""
            DROP MATERIALIZED VIEW IF EXISTS {view_name};
            CREATE MATERIALIZED VIEW {view_name}
            AS
            SELECT * FROM hms_managementarea
            WHERE category_id = {cat.pk};
            """

            with conn.cursor() as cursor:
                cursor.execute(sql)
            conn.commit()

    def refresh_views(self, category=""):

        db = settings.DATABASES['default']
        db_conn = "dbname = {} port = {} user = {} host = {} password = {}".format(
            db['NAME'],db['PORT'],db['USER'],db['HOST'],db['PASSWORD'])
        conn = psycopg2.connect(db_conn)

        for cat in ManagementAreaCategory.objects.all():

            if category and cat.name != category:
                continue
            
            view_name = self.make_hms_viewname(cat.name)

            print(f"refreshing materialized view {view_name}")

            with conn.cursor() as cursor:
                cursor.execute(f"REFRESH MATERIALIZED VIEW {view_name};")
            conn.commit()

        conn.close()
            
    def drop_views(self, category=""):

        db = settings.DATABASES['default']
        db_conn = "dbname = {} port = {} user = {} host = {} password = {}".format(
            db['NAME'],db['PORT'],db['USER'],db['HOST'],db['PASSWORD'])
        conn = psycopg2.connect(db_conn)

        mv_sql = """
        SELECT relname FROM pg_class
        WHERE relkind = 'm' AND relname LIKE 'mv_hms_%';
        """

        with conn.cursor() as cursor:
            cursor.execute(mv_sql)
            rows = cursor.fetchall()
        
            for row in rows:

                view_name = row[0]
                
                if category:
                    cat_view_name = self.make_hms_viewname(category)
                    if not cat_view_name == view_name:
                        continue
                
                print(f"dropping materialized view {view_name}")
                cursor.execute(f"DROP MATERIALIZED VIEW {view_name}")
                conn.commit()

        conn.close()