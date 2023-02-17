from django.conf.urls.i18n import i18n_patterns
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.views.generic.base import TemplateView
from django.urls import path
from django.conf import settings

from fpan.views.api import MVT, ResourceIdLookup
from fpan.views.user import FPANUserManagerView
from fpan.views.resource import (
    FPANResourceListView,
    FPANResourceEditLogView,
    FPANResourceData,
    FPANResourceTiles,
    FPANResourceCards,
    FPANResourceReportView,
    FPANRelatedResourcesView,
    FPANResourceEditorView,
)
from hms.views import server_error

handler500 = server_error
favicon_view = RedirectView.as_view(url=f'{settings.STATIC_URL}img/favicon/favicon.ico', permanent=True)

uuid_regex = settings.UUID_REGEX

urlpatterns = [
    # some site-level urls
    url(r'^favicon\.ico$', favicon_view),
    path("robots.txt",TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    path('grappelli/', include('grappelli.urls')), # grappelli URLS

    # override existing Arches urls in a few different instances
    url(
        r"^mvt/(?P<nodeid>%s)/(?P<zoom>[0-9]+|\{z\})/(?P<x>[0-9]+|\{x\})/(?P<y>[0-9]+|\{y\}).pbf$" % uuid_regex,
        MVT.as_view(),
        name="mvt",
    ),
    url(r"api/lookup$", ResourceIdLookup.as_view(), name="resource_lookup"),
    url(r"^user$", FPANUserManagerView.as_view(), name="user_profile_manager"),

    # the following are just pass through views so HMS can apply an additional permissions-based decorator
    url(r"^resource$", FPANResourceListView.as_view(), name="resource"),
    url(r"^resource/(?P<resourceid>%s)$" % uuid_regex, FPANResourceEditorView.as_view(), name="resource_editor"),
    url(r"^resource/(?P<resourceid>%s)/history$" % uuid_regex, FPANResourceEditLogView.as_view(), name="resource_edit_log"),
    #url(r"^resource/history$", FPANResourceEditLogView.as_view(), name="edit_history"),
    url(r"^resource/(?P<resourceid>%s)/data/(?P<formid>%s)$" % (uuid_regex, uuid_regex), FPANResourceData.as_view(), name="resource_data"),
    url(r"^resource/(?P<resourceid>%s)/tiles$" % uuid_regex, FPANResourceTiles.as_view(), name="resource_tiles"),
    url(r"^resource/(?P<resourceid>%s)/cards$" % uuid_regex, FPANResourceCards.as_view(), name="resource_cards"),
    url(r"^report/(?P<resourceid>%s)$" % uuid_regex, FPANResourceReportView.as_view(), name="resource_report"),

    # now include HMS urls
    url(r'^', include('hms.urls')),
    # include site_theme urls
    url(r'^', include('site_theme.urls')),

    # finally, include default Arches urls
    url(r'^', include('arches.urls')),
]
if settings.SHOW_LANGUAGE_SWITCH is True:
    urlpatterns = i18n_patterns(*urlpatterns)
if settings.DEBUG :
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
