from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import Polygon,MultiPolygon,fromstr
import os
import json

class Command(BaseCommand):

    help = 'creates a .json fixture from a shapefile.'

    def add_arguments(self, parser):
        parser.add_argument(
            '-y',
            '--yes',
            action='store_true',
            dest='yes',
            default=False,
            help='forces the continuation of any command that has a confirmation prompt',
        )
        parser.add_argument(
            '-db',
            '--setup_db',
            action='store_true',
            dest='setup_db',
            default=False,
            help='runs the setup_db command before beginning the load process. wipes everything.',
        )
        parser.add_argument("-c", "--components",
            nargs="*",
            help="email addresses to which the server setup notification will be set (defaults are added below)")
        pass

    def handle(self, *args, **options):

        self.convert_shp()

    def convert_shp(self):
    
        shp = r"C:\arches\fpan\data\shp-ref\from_julie\AllPublicLandsFL.shp"
        output = os.path.join('fpan','fixtures','managed_areas.json')
        # print os.path.abspath(output)
        # return
        ds = DataSource(shp)
        layer = ds[0]
        
        lookup = {
            'FL Dept. of Environmental Protection, Div. of Recreation and Parks':'State Parks',
            'FL Dept. of Agriculture and Consumer Services, Florida Forest Service':'State Forest',
            'FL Fish and Wildlife Conservation Commission':'Fish and Wildlife Conservation Commission',
            'FL Dept. of Environmental Protection, Florida Coastal Office':'Aquatic Preserve'
        }
        agencies = lookup.keys()
        
        ct = 0
        data = []
        for feat in layer:
            agency = feat.get("MANAGING_A")
            if not agency in agencies:
                continue
            name = feat.get("MANAME")
            cat = lookup[agency]
            ## case specific handling of geometries 11-27-17
            geotype = feat.geom.geom_type
            if geotype == "Polygon":
                geom = MultiPolygon(fromstr(feat.geom.wkt)).wkt
            if geotype == "MultiPolygon":
                geom = feat.geom.wkt
            f = {
                'model':'fpan.managedarea',
                'pk':ct,
                'fields':   {
                    'agency':agency,
                    'category':cat,
                    'geom':geom,
                    'name':name
                }
            }
            data.append(f)
            ct+=1
            if ct % 100 == 0:
                print ct
            elif ct % 10 == 0:
                print ct,

        with open(output,"wb") as out:
            json.dump(data,out,indent=2)
            