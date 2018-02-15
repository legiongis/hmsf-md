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
            'shapefile',
            help='path to input shapefile',
        )
        parser.add_argument(
            '--max',
            type=int,
            help='allows you to specify the max number of features that each fixture will have',
        )

    def handle(self, *args, **options):
        
        shp_path = options['shapefile']
        max_feat = options['max']
        self.convert_shp(shp_path, max_features=max_feat)

    def convert_shp(self,shp_path,max_features=None):
    
        # shp = r"C:\arches\fpan\data\shp-ref\from_julie\AllPublicLandsFL_edit.shp"
        output = r"C:\arches\fpan\repo\fpan-data\fixtures\managedareas0.json"
        ds = DataSource(shp_path)
        layer = ds[0]
        
        lookup = {
            'FL Dept. of Environmental Protection, Div. of Recreation and Parks':'State Park',
            'FL Dept. of Agriculture and Consumer Services, Florida Forest Service':'State Forest',
            'FL Fish and Wildlife Conservation Commission':'Fish and Wildlife Conservation Commission',
            'FL Dept. of Environmental Protection, Florida Coastal Office':'Aquatic Preserve'
        }
        agencies = lookup.keys()
        
        feat_ct = 0
        file_ct = 1
        data = []
        for feat in layer:
            agency = feat.get("MANAGING_A")
            if not agency in agencies:
                continue
            name = feat.get("MANAME")
            cat = lookup[agency]
            nickname = feat.get("NICKNAME")
            ## case specific handling of geometries 11-27-17
            geotype = feat.geom.geom_type
            if geotype == "Polygon":
                geom = MultiPolygon(fromstr(feat.geom.wkt)).wkt
            if geotype == "MultiPolygon":
                geom = feat.geom.wkt
            f = {
                'model':'fpan.managedarea',
                'pk':feat_ct,
                'fields':   {
                    'agency':agency,
                    'category':cat,
                    'geom':geom,
                    'name':name,
                    'nickname':nickname
                }
            }
            data.append(f)
            feat_ct+=1
            if feat_ct % 100 == 0:
                print feat_ct
            elif feat_ct % 10 == 0:
                print feat_ct,
                
            ## write partial if max_features has been specified
            if max_features:
                if feat_ct % max_features == 0:
                    output = output[:-6]+str(file_ct)+".json"
                    with open(output,"wb") as out:
                        json.dump(data,out,indent=2)
                    file_ct+=1
                    data = []

        if not feat_ct:
            with open(output,"wb") as out:
                json.dump(data,out,indent=2)
            