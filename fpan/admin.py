from django.contrib.gis import admin
from models.region import Region
from models.managedarea import ManagedArea

admin.site.register(Region, admin.GeoModelAdmin)
admin.site.register(ManagedArea, admin.GeoModelAdmin)
