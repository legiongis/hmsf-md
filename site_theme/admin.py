from django.contrib import admin

from site_theme.models import ProfileContent, ProfileLink

admin.site.register(ProfileLink)
admin.site.register(ProfileContent)
