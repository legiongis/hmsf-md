from django.core import management
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import subprocess
import psycopg2
import csv

class Command(BaseCommand):

    help = 'takes an input csv file and repairs the geometry field if necessary.'

    def add_arguments(self, parser):
        parser.add_argument(
            '-s',
            '--source',
            help='path to the csv',
        )
        parser.add_argument(
            '--geom_field',
            dest='geom_field',
            default='geom',
            help='name of the column that holds geometry',
        )

    def handle(self, *args, **options):

        print("this command is not fully implemented yet -- exiting.")
        exit()
        
        # self.repair_geometry(source=options['source'],geom_field=options['geom_field'])
        
    def repair_geometry(self,source='',geom_field='geom'):
        
        db = settings.DATABASES['default']
        db_conn = "dbname = {} user = {} host = {} password = {}".format(
            db['NAME'],db['USER'],db['HOST'],db['PASSWORD'])
        conn = psycopg2.connect(db_conn)
        cur = conn.cursor()
        
        outrows = []
        with open(source,"rb") as opencsv:
            reader = csv.reader(opencsv)
            header = next(reader)
            outrows.append(header)
            geo = header.index(geom_field)
            for row in reader:
                wkt = row.pop(geo)

                sql = '''
                SELECT ST_AsText(ST_MakeValid(ST_GeomFromText('{}')));
                '''.format(wkt)
                cur.execute(sql)
                new_wkt = cur.fetchall()[0][0]
                row.insert(geo,new_wkt)
                
                # def prepairGeometry(wkt,prepair_path):
                '''runs prepair on the input and returns the fixed polygon'''
                cmd = r'C:\arches\fpan\data\tools\prepair_win64\prepair.exe --wkt "{}"'.format(wkt)
                try:
                    prepaired_wkt = subprocess.check_output(cmd,shell=True)
                    
                except:
                    print("geometry couldn't be prepaired")
                    prepaired_wkt = wkt
                # return prepaired_wkt
                row.insert(geo,prepaired_wkt)
                
        with open(source.replace(".csv","_fixed.csv"),"wb") as output:
            writer = csv.writer(output)
            for row in outrows:
                writer.writerow(row)
