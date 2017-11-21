from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from hms.models import Scout, ScoutProfile


class ScoutProfileInline(admin.StackedInline):
    model = ScoutProfile
    verbose_name_plural = "Scout Profile"
    fk_name = 'user'

class ScoutProfileAdmin(admin.ModelAdmin):
    inlines = (ScoutProfileInline, )

    def get_inline_instance(self, request, obj=None):
        if not obj:
            return list()
        return super(ScoutProfileAdmin, self).get_inline_instance(request, obj)


admin.site.register(Scout, ScoutProfileAdmin)
