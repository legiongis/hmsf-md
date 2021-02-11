from django.conf.urls.i18n import i18n_patterns
from django.conf.urls import include, url
from django.views.generic import RedirectView
from django.conf import settings
from arches.app.views.auth import UserProfileView, GetClientIdView
from arches.app.views.user import UserManagerView
from fpan.views import api, main, auth, scout, search
from fpan.views.resource import (
    FPANResourceListView,
    FPANResourceEditLogView,
    FPANResourceData,
    FPANResourceTiles,
    FPANResourceCards,
    FPANResourceReportView,
    FPANRelatedResourcesView,
)

uuid_regex = settings.UUID_REGEX
handler500 = main.server_error

urlpatterns = [
    url(r'^$', main.index, name='fpan_home'),
    url(r'^profile', UserManagerView.as_view(), name="fpan_profile_manager"),
    url(r"^user$", auth.FPANUserManagerView.as_view(), name="user_profile_manager"),
    # url(r'^user/resource-instance-permissions', main.get_resource_instance_permissions, name='resource_instance_permissions'),
    url(r'^hms/home', main.hms_home, name='hms_home'),
    url(r'^state/home', main.state_home, name='state_home'),
    url(r'^regions/$', main.show_regions, name='show_regions'),
    url(r'^dashboard', main.fpan_dashboard, name='fpan_dashboard'),
    url(r'^index.htm', RedirectView.as_view(pattern_name='fpan_home', permanent=True)),
    url(r'^scout/signup', scout.scout_signup, name='scout_signup'),
    url(r'^scout/profile', scout.scout_profile, name='scout_profile'),
    url(r'^scouts/$', scout.scouts_dropdown, name='scouts_dropdown'),
    url(r'^scout-list-download/$', scout.scout_list_download, name='scout_list_download'),
    #url(r'^search$', search.FPANSearchView.as_view(), name="search_home"),
    url(
        r"^mvt/(?P<nodeid>%s)/(?P<zoom>[0-9]+|\{z\})/(?P<x>[0-9]+|\{x\})/(?P<y>[0-9]+|\{y\}).pbf$" % uuid_regex,
        api.MVT.as_view(),
        name="mvt",
    ),
    url(r'^auth/user_profile$', UserProfileView.as_view(), name='user_profile'),
    url(r'^auth/get_client_id$', GetClientIdView.as_view(), name='get_client_id'),
    url(r'^auth/password$', auth.change_password, name='change_password'),
    url(r'^auth/(?P<login_type>[\w-]+)', auth.auth, name='auth'),
    url(r'^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/',
        auth.activate, name='activate'),
    url(r'^auth/', RedirectView.as_view(pattern_name='fpan_home', permanent=True)),
    url(r"api/lookup$", api.ResourceIdLookup.as_view(), name="resource_lookup"),

    # the following are just pass through views so FPAN can add custom permissions
    url(r"^resource$", FPANResourceListView.as_view(), name="resource"),
    url(r"^resource/(?P<resourceid>%s)/history$" % uuid_regex, FPANResourceEditLogView.as_view(), name="resource_edit_log"),
    url(r"^resource/history$", FPANResourceEditLogView.as_view(), name="edit_history"),
    url(r"^resource/(?P<resourceid>%s)/data/(?P<formid>%s)$" % (uuid_regex, uuid_regex), FPANResourceData.as_view(), name="resource_data"),
    url(r"^resource/(?P<resourceid>%s)/tiles$" % uuid_regex, FPANResourceTiles.as_view(), name="resource_tiles"),
    url(r"^resource/(?P<resourceid>%s)/cards$" % uuid_regex, FPANResourceCards.as_view(), name="resource_cards"),
    url(r"^report/(?P<resourceid>%s)$" % uuid_regex, FPANResourceReportView.as_view(), name="resource_report"),
    url(r"^report/(?P<resourceid>%s)$" % uuid_regex, FPANResourceReportView.as_view(), name="resource_report"),

    url(r'^', include('arches.urls')),
]
if settings.SHOW_LANGUAGE_SWITCH is True:
    urlpatterns = i18n_patterns(*urlpatterns)
