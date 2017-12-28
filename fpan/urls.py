from django.conf.urls import include, url
from django.contrib.gis import admin
from django.views.generic import RedirectView, TemplateView
from arches.app.views import main
from . import views
from django.views.defaults import page_not_found


urlpatterns = [
    url(r'^$', views.index, name='fpan_home'),
    url(r'^index.htm', RedirectView.as_view(pattern_name='fpan_home', permanent=True)),
    url(r'^auth/password$', views.change_password, name='change_password'),
    url(r'^auth/(?P<login_type>[\w-]+)', views.auth, name='auth'),
    url(r'^auth/', RedirectView.as_view(pattern_name='fpan_home', permanent=True)),
    url(r'^regions/$', views.show_regions, name='show_regions'),
    url(r'^scout/signup', views.scout_signup, name='scout_signup'),
    url(r'^scout/profile', views.scout_profile, name='scout_profile'),
    url(r'^404/$', TemplateView.as_view(template_name='404.html')),
    url(r'^500/$', TemplateView.as_view(template_name='500.html')),
    url(r'^hms/home', views.hms_home, name='hms_home'),
    url(r'^state/home', views.state_home, name='state_home'),
    url(r'^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/',
        views.activate, name='activate'),
    url(r'^', include('arches.urls')),
    url(r'^hms/', include('hms.urls')),
    url(r'^admin/', admin.site.urls),
]
