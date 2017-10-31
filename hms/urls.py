from django.conf.urls import include, url
from django.contrib.gis import admin
# from django.contrib import admin
from . import views

urlpatterns = [
    url(r'^scouts/$', views.scouts_dropdown, name='scouts_dropdown'),
]


    # 
    # 
    # url(r'^scout/signup', views.scout_signup, name='scout_signup'),
    # url(r'^regions/$', views.show_regions, name='show_regions'),
    # url(r'^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/',
    #     views.activate, name='activate'),
