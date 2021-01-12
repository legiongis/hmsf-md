import os
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import MultiPolygon, Polygon

from hms.models import ManagementArea, ManagementAreaGroup

class Command(BaseCommand):

    help = 'Loads Management Areas from shapefile.'

    def add_arguments(self, parser):
        parser.add_argument(
            'operation',
            choices=["load", "remove", "load-ids"],
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

    def handle(self, *args, **options):

        if options['operation'] == "load":
            self.load_areas(options['source'], options['group_names'])
        if options['operation'] == "remove":
            self.remove_areas(options['load_id'])
        if options['operation'] == "load-ids":
            self.list_load_ids()

    def load_areas(self, source, group_names):

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
            for group in add_to_groups:
                group.areas.add(new_ma)
            load_ct += 1

        print(f"{load_ct} Management Areas loaded.")
        print(f"load id: {load_id}")
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

    def list_load_ids(self):

        ids = ManagementArea.objects.all().values("load_id").distinct()
        for id in ids:
            print(id)
