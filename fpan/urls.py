from django.conf.urls import include, url
from django.contrib.gis import admin
from django.views.generic import RedirectView, TemplateView
from arches.app.views import main
from django.conf import settings
from . import views
from django.views.defaults import page_not_found

uuid_regex = settings.UUID_REGEX
handler500 = views.server_error

urlpatterns = [
    url(r'^$', views.index, name='fpan_home'),
    url(r'^index.htm', RedirectView.as_view(pattern_name='fpan_home', permanent=True)),
    url(r'^auth/password$', views.change_password, name='change_password'),
    url(r'^auth/(?P<login_type>[\w-]+)', views.auth, name='auth'),
    url(r'^auth/', RedirectView.as_view(pattern_name='fpan_home', permanent=True)),
    url(r'^regions/$', views.show_regions, name='show_regions'),
    url(r'^scout/signup', views.scout_signup, name='scout_signup'),
    url(r'^scout/profile', views.scout_profile, name='scout_profile'),
    url(r'^hms/home', views.hms_home, name='hms_home'),
    url(r'^state/home', views.state_home, name='state_home'),
    url(r'^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/',
        views.activate, name='activate'),
    url(r'^report/(?P<resourceid>%s)$' % uuid_regex, views.FPANResourceReportView.as_view(), name='resource_report'),
    url(r'^search$', views.FPANSearchView.as_view(), name="search_home"),
    url(r'^search/resources$', views.search_results, name="search_results"),
    url(r'^', include('arches.urls')),
    url(r'^hms/', include('hms.urls')),
    url(r'^admin/', admin.site.urls),
    url(r'^dashboard', views.fpan_dashboard, name='fpan_dashboard'),
]
