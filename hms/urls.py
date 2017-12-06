from django.conf.urls import include, url
from django.contrib.gis import admin
# from django.contrib import admin
from . import views
import fpan.views as fpan_views

urlpatterns = [
    url(r'^scouts/$', views.scouts_dropdown, name='scouts_dropdown'),
    url(r'^home', fpan_views.hms_home, name='hms_home'),    
]

