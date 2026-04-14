from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib.auth.decorators import user_passes_test
from django.views.generic import RedirectView
from django.views.generic.base import TemplateView
from django.urls import path, re_path, include
from django.conf import settings

from arches.app.views import search

from fpan.views.api import MVT
from fpan.views.user import FPANUserManagerView
from fpan.views.resource import (
    FPANResourceListView,
    FPANResourceEditLogView,
    FPANResourceData,
    FPANResourceTiles,
    FPANResourceCards,
    FPANResourceReportView,
    FPANResourceEditorView,
)
from hms.views import server_error

handler500 = server_error
favicon_view = RedirectView.as_view(
    url=f"{settings.STATIC_URL}img/favicon/favicon.ico", permanent=True
)

uuid_regex = settings.UUID_REGEX


def is_not_anonymous(user):
    return user.username != "anonymous"


urlpatterns = [
    # some site-level urls
    re_path(r"^favicon\.ico$", favicon_view),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
    ),
    path("grappelli/", include("grappelli.urls")),  # grappelli URLS
    # override existing Arches urls in a few different instances
    re_path(
        r"^mvt/(?P<nodeid>%s)/(?P<zoom>[0-9]+|\{z\})/(?P<x>[0-9]+|\{x\})/(?P<y>[0-9]+|\{y\}).pbf$"
        % uuid_regex,
        MVT.as_view(),
        name="mvt",
    ),
    re_path(r"^user$", FPANUserManagerView.as_view(), name="user_profile_manager"),
    # the following are just pass through views so HMS can apply an additional permissions-based decorator
    re_path(r"^resource$", FPANResourceListView.as_view(), name="resource"),
    re_path(
        r"^resource/(?P<resourceid>%s)$" % uuid_regex,
        FPANResourceEditorView.as_view(),
        name="resource_editor",
    ),
    re_path(
        r"^resource/(?P<resourceid>%s)/history$" % uuid_regex,
        FPANResourceEditLogView.as_view(),
        name="resource_edit_log",
    ),
    # url(r"^resource/history$", FPANResourceEditLogView.as_view(), name="edit_history"),
    re_path(
        r"^resource/(?P<resourceid>%s)/data/(?P<formid>%s)$" % (uuid_regex, uuid_regex),
        FPANResourceData.as_view(),
        name="resource_data",
    ),
    re_path(
        r"^resource/(?P<resourceid>%s)/tiles$" % uuid_regex,
        FPANResourceTiles.as_view(),
        name="resource_tiles",
    ),
    re_path(
        r"^resource/(?P<resourceid>%s)/cards$" % uuid_regex,
        FPANResourceCards.as_view(),
        name="resource_cards",
    ),
    re_path(
        r"^report/(?P<resourceid>%s)$" % uuid_regex,
        FPANResourceReportView.as_view(),
        name="resource_report",
    ),
    # override Arches /search view to apply login_required
    re_path(
        r"^search$",
        user_passes_test(is_not_anonymous, login_url="/auth/")(
            search.SearchView.as_view()
        ),
        name="search_home",
    ),
    re_path(
        r"^search/terms$",
        user_passes_test(is_not_anonymous, login_url="/auth/")(search.search_terms),
        name="search_terms",
    ),
    re_path(
        r"^search/resources$",
        user_passes_test(is_not_anonymous, login_url="/auth/")(search.search_results),  # type: ignore (this is an upstream issue in arches)
        name="search_results",
    ),
    re_path(
        r"^search/time_wheel_config$",
        user_passes_test(is_not_anonymous, login_url="/auth/")(
            search.time_wheel_config
        ),
        name="time_wheel_config",
    ),
    re_path(
        r"^search/export_results$",
        user_passes_test(is_not_anonymous, login_url="/auth/")(search.export_results),
        name="export_results",
    ),
    re_path(
        r"^search/get_export_file$",
        user_passes_test(is_not_anonymous, login_url="/auth/")(search.get_export_file),  # type: ignore (this is an upstream issue in arches)
        name="get_export_file",
    ),
    re_path(
        r"^search/get_dsl$",
        user_passes_test(is_not_anonymous, login_url="/auth/")(
            search.get_dsl_from_search_string
        ),
        name="get_dsl",
    ),
    # now include HMS urls
    re_path(r"^", include("hms.urls")),
    # include site_theme urls
    re_path(r"^", include("site_theme.urls")),
    # finally, include default Arches urls
    re_path(r"^", include("arches.urls")),
    # django-docs urls
    re_path(r"^docs/", include("docs.urls")),
]
if settings.SHOW_LANGUAGE_SWITCH is True:
    urlpatterns = i18n_patterns(*urlpatterns)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
