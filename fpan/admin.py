from django.contrib.gis import admin
from fpan.models.region import Region
from fpan.models.managedarea import ManagedArea

admin.site.register(Region, admin.GeoModelAdmin)
admin.site.register(ManagedArea, admin.GeoModelAdmin)
