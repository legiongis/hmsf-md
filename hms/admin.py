from django.contrib.gis import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from hms.models import (
    Scout,
    ScoutProfile,
    LandManager,
    LandManagerProfile,
    ManagementAgency,
    ManagementArea,
    ManagementAreaGroup,
)


class ScoutProfileInline(admin.StackedInline):
    model = ScoutProfile
    verbose_name_plural = "Scout Profile"
    fk_name = 'user'

class ScoutProfileAdmin(admin.ModelAdmin):
    search_fields = ["username", "first_name", "last_name"]
    inlines = (ScoutProfileInline, )

    def get_inline_instance(self, request, obj=None):
        if not obj:
            return list()
        return super(ScoutProfileAdmin, self).get_inline_instance(request, obj)

admin.site.register(Scout, ScoutProfileAdmin)

## PROBLEM: disabling this inline interface for now, even though it should
## successfully mimic the (kind of working) scout interface. Use a more simple
## admin class without the inline.
# class LandManagerProfileInline(admin.StackedInline):
#     model = LandManagerProfile
#     verbose_name_plural = "Land Manager Profile"
#     filter_horizontal = ('individual_areas', 'grouped_areas')
#     fk_name = 'user'
#
# class LandManagerProfileAdmin(admin.ModelAdmin):
#     search_fields = ["username"]
#     inlines = (LandManagerProfileInline, )
#
#     def get_inline_instance(self, request, obj=None):
#         if not obj:
#             return list()
#         return super(LandManagerProfileAdmin, self).get_inline_instance(request, obj)

# admin.site.register(LandManager, LandManagerProfileAdmin)

class LandManagerProfileAdmin(admin.ModelAdmin):
    filter_horizontal = ('individual_areas', 'grouped_areas')

admin.site.register(LandManagerProfile, LandManagerProfileAdmin)

## this is registered so that a new Land Manager can be made directly from the
## Land Manager Profile interface, using the green + button.
admin.site.register(LandManager)


class ManagementAreaGroupAdmin(admin.ModelAdmin):
    filter_horizontal = ('areas',)

admin.site.register(ManagementArea, admin.GeoModelAdmin)
admin.site.register(ManagementAgency)
admin.site.register(ManagementAreaGroup, ManagementAreaGroupAdmin)
