import logging
from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache
from django.views.generic import View
from django.http import HttpResponse, Http404
from django.urls import reverse
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.utils.translation import ugettext as _
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string, get_template
from django.views.decorators.csrf import csrf_exempt

from arches.app.models.system_settings import settings
from arches.app.views.user import UserManagerView

from fpan.utils.tokens import account_activation_token
from fpan.utils.permission_backend import user_is_land_manager, user_is_scout

from hms.models import Scout
from hms.forms import ScoutForm, ScoutProfileForm

logger = logging.getLogger(__name__)


class LoginView(View):
    def get(self, request):

        login_type = request.GET.get("t", "landmanager")
        if request.GET.get("logout", None) is not None:

            if user_is_scout(request.user):
                login_type = "scout"
            # send land managers and admin back to the landmanager login
            else:
                login_type = "landmanager"

            logout(request)
            # need to redirect to 'auth' so that the user is set to anonymous via the middleware
            return redirect(f"/auth/?t={login_type}")
        else:
            next = request.GET.get("next", None)
            return render(request, "login.htm", {
                "auth_failed": False,
                "next": next,
                "login_type": login_type,
            })

    def post(self, request):
        # POST request is taken to mean user is logging in
        login_type = request.GET.get("t", "landmanager")
        next = request.GET.get("next", None)
        username = request.POST.get("username", None)
        password = request.POST.get("password", None)
        user = authenticate(username=username, password=password)

        if user is not None and user.is_active:

            auth_attempt_success = True
            # these conditionals ensure that scouts and land managers must
            # use the correct login portals
            if user_is_land_manager(user) and login_type != "landmanager":
                auth_attempt_success = False

            if user_is_scout(user) and login_type != "scout":
                auth_attempt_success = False
            
            # if user survives above checks, login
            if auth_attempt_success is True:
                login(request, user)
                user.password = ""

                    # set next redirect based on user type if not previously set
                if next is None:
                    if user.is_superuser:
                        next = request.POST.get("next", reverse("search_home"))
                    elif user_is_land_manager(user):
                        next = request.POST.get("next", reverse("state_home"))
                    elif user_is_scout(user):
                        next = request.POST.get("next", reverse("hms_home"))
                    else:
                        next = request.POST.get("next", reverse("search_home"))

                return redirect(next)

        return render(request, "login.htm", {
            "auth_failed": True,
            "next": next,
            "login_type": login_type
        }, status=401)

def activate(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = Scout.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, Scout.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        user = authenticate(username=user.username, password=user.password)
        scout_form = ScoutForm(instance=user)
        scout_profile_form = ScoutProfileForm()
        return redirect('auth',login_type='hms')
    else:
        return HttpResponse('Activation link is invalid!')


class FPANUserManagerView(UserManagerView):
    """ this view powers the modified profile manager, and is built from the analogous
        view in core arches. The main difference is that different forms are passed
        to the view based on what type of user (land manager or scout) is logged
        in, and different templates are used to render."""
    pass
