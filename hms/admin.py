from django.contrib.gis import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from hms.models import (
    Scout,
    ScoutProfile,
    LandManager,
    ManagementAgency,
    ManagementArea,
    ManagementAreaGroup,
    ManagementAreaCategory,
)


class ScoutProfileInline(admin.StackedInline):
    model = ScoutProfile
    verbose_name_plural = "Scout Profile"
    fk_name = 'user'
    readonly_fields = ('site_access_rules_formatted', 'accessible_sites_formatted')

class ScoutProfileAdmin(admin.ModelAdmin):
    search_fields = ["username", "first_name", "last_name"]
    inlines = (ScoutProfileInline, )

    def get_inline_instance(self, request, obj=None):
        if not obj:
            return list()
        return super(ScoutProfileAdmin, self).get_inline_instance(request, obj)

admin.site.register(Scout, ScoutProfileAdmin)

class LandManagerAdmin(admin.ModelAdmin):
    filter_horizontal = ('individual_areas', 'grouped_areas')
    search_fields = ('username', )
    exclude = ('username', )
    readonly_fields = ('site_access_rules_formatted', 'accessible_sites_formatted')

admin.site.register(LandManager, LandManagerAdmin)

## this is registered so that a new Land Manager can be made directly from the
## Land Manager Profile interface, using the green + button.
# admin.site.register(LandManager)

class ManagementAreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'management_level', 'category', 'management_agency', 'load_id')
    list_filter = ('category', 'management_level', 'management_agency', 'load_id')
    readonly_fields = ('display_name', )
    search_fields = ('name', )

class ManagementAreaGroupAdmin(admin.ModelAdmin):
    filter_horizontal = ('areas',)

admin.site.register(ManagementArea, ManagementAreaAdmin)
admin.site.register(ManagementAgency)
admin.site.register(ManagementAreaCategory)
admin.site.register(ManagementAreaGroup, ManagementAreaGroupAdmin)
