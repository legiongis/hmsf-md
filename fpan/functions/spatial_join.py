import uuid
from django.core.exceptions import ValidationError
from arches.app.functions.base import BaseFunction
from arches.app.models import models
from arches.app.models.tile import Tile
from arches.app.models.system_settings import settings
import json

details = {
    'name': 'Spatial Join',
    'type': 'node',
    'description': 'perform attribute transfer based on comparison to local PostGIS table',
    'defaultconfig': {"spatial_node_id":"","table_name":"","field_name":"","target_node_id":""},
    'classname': 'SpatialJoin',
    'component': 'views/components/functions/spatial-join'
}

class SpatialJoin(BaseFunction):

    def attribute_from_postgis(field,table,wkt):
    
        sql = '''
        SELECT {0} FROM {1}
            WHERE
            ST_Intersects(
              ST_GeomFromText(
               {2}, 4326
              ),
              {1}.geom
            );
        '''.format(field,table,wkt)
    
    def save(self,tile,request):
    
        configs = self.config
        print tile.data

        print 'calling save'

    def on_import(self):
        print 'calling on import'

    def get(self):
        print 'calling get'

    def delete(self):
        print 'calling delete'
