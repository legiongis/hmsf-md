from django.conf.urls import include, url
from django.contrib.gis import admin
from . import views

urlpatterns = [
    url(r'^$', views.index, name='home'),
    url(r'^scout/signup', views.scout_signup, name='scout_signup'),
    url(r'^scout/profile', views.scout_profile, name='scout_profile'),
    url(r'^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/',
        views.activate, name='activate'),
    url(r'^', include('arches.urls')),
    url(r'^hms/', include('hms.urls')),
    url(r'^admin/', admin.site.urls),
]


    # 
    # url(r'^scouts/$', views.scouts_dropdown, name='scouts_dropdown'),
    # 
    # url(r'^regions/$', views.show_regions, name='show_regions'),
    
