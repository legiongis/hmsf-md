from django.contrib.gis import admin
from fpan.models.region import Region
from fpan.models.managedarea import ManagedArea

class ManagedAreaAdmin(admin.GeoModelAdmin):

    search_fields = ["name"]

admin.site.register(Region, admin.GeoModelAdmin)
admin.site.register(ManagedArea, ManagedAreaAdmin)
