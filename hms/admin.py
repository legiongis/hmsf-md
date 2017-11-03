from django.contrib import admin
from hms.models import Scout, ScoutProfile
# Register your models here.
class ScoutInline(admin.TabularInline):
    model = Scout

class ScoutProfileInline(admin.StackedInline):
    model = ScoutProfile

class ScoutAdmin(admin.ModelAdmin):
    inlines = [
        ScoutInline,
        ScoutProfileInline,
    ]

admin.site.register(Scout, ScoutAdmin)
