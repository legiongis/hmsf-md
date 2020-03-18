from django.conf.urls import include, url
from django.views.generic import RedirectView
from django.conf import settings
from fpan.views import main, report, auth, scout, search

uuid_regex = settings.UUID_REGEX
handler500 = main.server_error

urlpatterns = [
    url(r'^$', main.index, name='fpan_home'),
    url(r'^hms/home', main.hms_home, name='hms_home'),
    url(r'^state/home', main.state_home, name='state_home'),
    url(r'^regions/$', main.show_regions, name='show_regions'),
    url(r'^dashboard', main.fpan_dashboard, name='fpan_dashboard'),
    url(r'^index.htm', RedirectView.as_view(pattern_name='fpan_home', permanent=True)),
    url(r'^scout/signup', scout.scout_signup, name='scout_signup'),
    url(r'^scout/profile', scout.scout_profile, name='scout_profile'),
    url(r'^scouts/$', scout.scouts_dropdown, name='scouts_dropdown'),
    url(r'^scout-list-download/$', scout.scout_list_download, name='scout_list_download'),
    url(r'^report/(?P<resourceid>%s)$' % uuid_regex, report.FPANResourceReportView.as_view(), name='resource_report'),
    # url(r'^search$', search.FPANSearchView.as_view(), name="search_home"),
    # url(r'^search/resources$', search.search_results, name="search_results"),
    url(r'^auth/password$', auth.change_password, name='change_password'),
    url(r'^auth/(?P<login_type>[\w-]+)', auth.auth, name='auth'),
    url(r'^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/',
        auth.activate, name='activate'),
    url(r'^auth/', RedirectView.as_view(pattern_name='fpan_home', permanent=True)),
    url(r'^', include('arches.urls')),
]
