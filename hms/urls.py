from django.views.generic import RedirectView
from django.urls import path, re_path

from hms.views import (
    index,
    about,
    scout_signup,
    scouts_dropdown,
    scout_list_download,
    login_patch,
    LoginView,
    ScoutProfileView,
    activate,
    activate_page,
    DownloadScoutReportPhotos,
)

urlpatterns = [
    re_path(r"^$", index, name="fpan_home"),
    re_path(
        r"^index.htm", RedirectView.as_view(pattern_name="fpan_home", permanent=True)
    ),
    path("about/", about, name="about"),
    re_path(
        r"^user/scout-profile$",
        ScoutProfileView.as_view(),
        name="scout_profile_manager",
    ),
    re_path(
        r"^hms/home",
        RedirectView.as_view(pattern_name="scout_profile_manager", permanent=True),
    ),
    re_path(
        r"^state/home",
        RedirectView.as_view(pattern_name="user_profile_manager", permanent=True),
    ),
    re_path(
        r"^dashboard",
        RedirectView.as_view(pattern_name="user_profile_manager", permanent=True),
    ),
    # this url is meant to be sensible but not guessable
    re_path(r"^scout/signup-850-595-0050", scout_signup, name="scout_signup"),
    re_path(r"^scouts/$", scouts_dropdown, name="scouts_dropdown"),
    re_path(r"^scout-list-download/$", scout_list_download, name="scout_list_download"),
    path(
        "auth/state",
        login_patch,
        {"login_type": "landmanager"},
        name="state_login_redirect",
    ),
    path(
        "auth/scout", login_patch, {"login_type": "scout"}, name="scout_login_redirect"
    ),
    re_path(r"^auth/$", LoginView.as_view(), name="auth"),
    path("activate/", activate, name="activate"),
    path("activate/<str:uidb64>/<str:token>/", activate_page, name="activate_page"),
    # download report photos
    path(
        "report/photos",
        view=DownloadScoutReportPhotos.as_view(),
        name="download-report-photos",
    ),
]
