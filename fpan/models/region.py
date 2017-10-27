# # This is an auto-generated Django model module created by ogrinspect.
from django.contrib.gis.db import models

class Region(models.Model):
    region = models.CharField(max_length=254)
    geom = models.MultiPolygonField(srid=4362)

# Auto-generated `LayerMapping` dictionary for Region model
region_mapping = {
    'region' : 'REGION',
    'geom' : 'MULTIPOLYGON',
}
