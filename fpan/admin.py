from django.contrib.gis import admin
from models.region import Region

admin.site.register(Region, admin.GeoModelAdmin)
