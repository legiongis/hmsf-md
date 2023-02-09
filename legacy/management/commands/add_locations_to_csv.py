import os
import csv
import json
import psycopg2
from django.contrib.gis.geos import GEOSGeometry
from django.core.management.base import BaseCommand, CommandError
from fpan.functions.spatial_join import attribute_from_postgis



class Command(BaseCommand):

    help = 'adds new fields to a csv using spatial join with postgis tables'

    def add_arguments(self, parser):
        parser.add_argument(
            '-s',
            '--source',
            help='path to the csv',
        )

    def handle(self, *args, **options):

        self.join_locations(options['source'])

    def join_locations(self, csv_path):
    
        location_joins = [
            {
                "csv_field": "FPAN_REG",
                "db_table": "fpan_region",
                "db_column": "name",
            },
            {
                "csv_field": "MANAME",
                "db_table": "fpan_managedarea",
                "db_column": "name",
            },
            {
                "csv_field": "MANAGING_A",
                "db_table": "fpan_managedarea",
                "db_column": "agency",
            },
            {
                "csv_field": "MA_CAT",
                "db_table": "fpan_managedarea",
                "db_column": "category",
            },
        ]

        print(csv_path)
        out_rows = list()
        with open(csv_path, "r") as openf:
            reader = csv.DictReader(openf)
            for row in reader:
                resid = row["ResourceID"]
                geom = GEOSGeometry(row["geom"])
                geojson = json.loads(geom.geojson)
                for join in location_joins:
                    vals = attribute_from_postgis(join['db_table'], join['db_column'], geojson)
                    fixed_vals = list()
                    for v in vals:
                        if v == "State Park":
                            v = "State Parks"
                        if "," in v:
                            fixed_vals.append(f'"{v}"')
                        else:
                            fixed_vals.append(v)
                    row[join['csv_field']] = ",".join(fixed_vals)
                out_rows.append(row)
        
        out_csv_path = csv_path.replace(".csv", "-ready.csv")
        with open(out_csv_path, "w", newline="") as outf:
            writer = csv.DictWriter(outf, fieldnames=out_rows[0].keys())
            writer.writeheader()
            [writer.writerow(row) for row in out_rows]
