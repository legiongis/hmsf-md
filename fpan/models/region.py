# # This is an auto-generated Django model module created by ogrinspect.
from django.contrib.gis.db import models

class Region(models.Model):
    name = models.CharField(max_length=254)
    region_code = models.CharField(max_length=4)
    geom = models.MultiPolygonField()

    # Returns the string representation of the model.
    def __unicode__(self):              # __unicode__ on Python 2
        return self.name
