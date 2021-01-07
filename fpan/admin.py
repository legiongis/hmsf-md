from django.contrib.gis import admin
from fpan.models import Region, ManagedArea, ManagerProfile

class ManagedAreaAdmin(admin.GeoModelAdmin):

    search_fields = ["name"]

admin.site.register(Region, admin.GeoModelAdmin)
admin.site.register(ManagedArea, ManagedAreaAdmin)

from fpan.models import Agency, ManagementArea, ManagementAreaType, ManagementAreaGroup

class ManagementAreaGroupAdmin(admin.ModelAdmin):
    filter_horizontal = ('areas',)

class ManagerProfileAdmin(admin.ModelAdmin):
    filter_horizontal = ('areas', 'area_groups')

admin.site.register(Agency)
admin.site.register(ManagementArea, admin.GeoModelAdmin)
admin.site.register(ManagementAreaType)
admin.site.register(ManagementAreaGroup, ManagementAreaGroupAdmin)
admin.site.register(ManagerProfile, ManagerProfileAdmin)
