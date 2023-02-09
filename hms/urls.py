from django.conf.urls import url
from django.views.generic import RedirectView
from django.urls import path

from hms.views import (
    index,
    about,
    hms_home,
    scout_signup,
    scouts_dropdown,
    scout_list_download,
    login_patch,
    LoginView,
    activate,
    activate_page,
)

urlpatterns = [
    url(r'^$', index, name='fpan_home'),
    url(r'^index.htm', RedirectView.as_view(pattern_name='fpan_home', permanent=True)),
    url(r'^about$', about, name='about'),
    url(r"^user/scout-profile$", hms_home, name="scout_profile_manager"),
    url(r'^hms/home', RedirectView.as_view(pattern_name='scout_profile_manager', permanent=True)),
    url(r'^state/home', RedirectView.as_view(pattern_name='user_profile_manager', permanent=True)),
    url(r'^dashboard', RedirectView.as_view(pattern_name='user_profile_manager', permanent=True)),

    url(r'^scout/signup', scout_signup, name='scout_signup'),
    url(r'^scouts/$', scouts_dropdown, name='scouts_dropdown'),
    url(r'^scout-list-download/$', scout_list_download, name='scout_list_download'),

    path("auth/state", login_patch, {'login_type':'landmanager'}, name="state_login_redirect"),
    path("auth/scout", login_patch, {'login_type':'scout'}, name="scout_login_redirect"),
    url(r"^auth/", LoginView.as_view(), name="auth"),
    path("activate/", activate, name='activate'),
    path("activate/<str:uidb64>/<str:token>/", activate_page, name='activate_page'),
]
