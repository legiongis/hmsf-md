from django.conf.urls import include, url
from django.contrib.gis import admin
# from django.contrib import admin
from . import views

urlpatterns = [
    url(r'^scouts/$', views.scouts_dropdown, name='scouts_dropdown'),    
]

# url(r'^scout/(?P<username>\w+)/', views.scout_profile, name='scout_profile'),
