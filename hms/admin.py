from django.contrib.gis import admin
from hms.models import (
    Scout,
    ScoutProfile,
    LandManager,
    ManagementAgency,
    ManagementArea,
    ManagementAreaGroup,
    ManagementAreaCategory,
    FPANRegion,
)


class ScoutProfileInline(admin.StackedInline):
    model = ScoutProfile
    verbose_name_plural = "Scout Profile"
    fk_name = "user"
    readonly_fields = ("site_access_rules_formatted", "accessible_sites_formatted")


class ScoutProfileAdmin(admin.ModelAdmin):
    list_display = ("username", "interests", "fpan_regions")
    search_fields = ["username", "first_name", "last_name"]
    inlines = (ScoutProfileInline,)

    def get_inline_instance(self, request, obj=None):
        if not obj:
            return list()
        return super(ScoutProfileAdmin, self).get_inline_instance(request, obj)  # pyright: ignore[reportAttributeAccessIssue]

    def fpan_regions(self, obj):
        return ", ".join([i.name for i in obj.scoutprofile.fpan_regions2.all()])

    def interests(self, obj):
        return obj.scoutprofile.site_interest_type


admin.site.register(Scout, ScoutProfileAdmin)


class LandManagerAdmin(admin.ModelAdmin):
    list_display = (
        "username",
        "site_access_mode",
        "management_agency",
        "management_area_names",
        "management_area_group_names",
    )
    list_filter = (
        "site_access_mode",
        "management_agency",
    )
    filter_horizontal = ("individual_areas", "grouped_areas")
    search_fields = ("username",)
    exclude = ("username",)
    readonly_fields = ("site_access_rules_formatted", "accessible_sites_formatted")

    def management_area_names(self, obj):
        return ", ".join([i.name for i in obj.individual_areas.all()])

    def management_area_group_names(self, obj):
        return ", ".join([i.name for i in obj.grouped_areas.all()])


admin.site.register(LandManager, LandManagerAdmin)


class ManagementAreaAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "management_level",
        "category",
        "management_agency",
        "load_id",
    )
    list_filter = ("category", "management_level", "management_agency", "load_id")
    readonly_fields = ("display_name",)
    search_fields = ("name",)


class ManagementAreaGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "management_area_names")
    filter_horizontal = ("areas",)

    def management_area_names(self, obj):
        return ", ".join([i.name for i in obj.areas.all()])


admin.site.register(ManagementArea, ManagementAreaAdmin)
admin.site.register(ManagementAgency)
admin.site.register(ManagementAreaCategory)
admin.site.register(ManagementAreaGroup, ManagementAreaGroupAdmin)
admin.site.register(FPANRegion)
