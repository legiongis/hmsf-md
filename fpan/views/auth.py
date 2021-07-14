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
        next = request.GET.get("next", reverse("search_home"))

        if request.GET.get("logout", None) is not None:

            if user_is_scout(request.user):
                login_type = "scout"
            # send land managers and admin to the landmanager login
            else:
                login_type = "landmanager"

            logout(request)
            # need to redirect to 'auth' so that the user is set to anonymous via the middleware
            return redirect(f"/auth/?t={login_type}")
        else:

            return render(request, "login.htm", {
                "auth_failed": False,
                "next": next,
                "login_type": login_type,
            })

    def post(self, request):
        login_type = request.GET.get("t", "anonymous")
        # POST request is taken to mean user is logging in
        auth_attempt_success = None
        username = request.POST.get("username", None)
        password = request.POST.get("password", None)
        user = authenticate(username=username, password=password)
        next = request.POST.get("next", reverse("home"))

        login_fail = render(request, "login.htm", {
            "auth_failed": True,
            "next": next,
            "login_type": login_type
        }, status=401)

        if user is not None and user.is_active:

            # these conditionals ensure that scouts and land managers must
            # use the correct login portals
            print(user_is_land_manager(user))
            print(login_type)
            if user_is_land_manager(user) and login_type != "landmanager":
                return login_fail

            if user_is_scout(user) and login_type != "scout":
                return login_fail

            login(request, user)
            user.password = ""
            auth_attempt_success = True
            return redirect(next)

        return login_fail


@never_cache
@csrf_exempt
def old_auth(request, login_type):

    if not login_type in ['hms','state','logout']:
        raise Http404("not found")

    if login_type == 'logout':
        logger.info(f"logging user out via fpan.views.auth: {request.user.username}")
        logout(request)
        return redirect('fpan_home')

    auth_attempt_success = None

    # POST request is taken to mean user is logging in
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)

        if user is not None and user.is_active:
            logger.info(f"logging user in via fpan.views.auth: {username}")
            if login_type == "hms":
                if user_is_scout(user) or user.is_superuser:
                    login(request, user)
                    auth_attempt_success = True
                else:
                    auth_attempt_success = False
            elif login_type == "state":
                if user_is_land_manager(user):
                    login(request, user)
                    auth_attempt_success = True
                else:
                    auth_attempt_success = False
            user.password = ''
        else:
            auth_attempt_success = False

    next = request.GET.get('next', reverse('home'))
    if auth_attempt_success:
        if user.is_superuser:
            return redirect('search_home')
        if login_type == "hms":
            return redirect('hms_home')
        if login_type == "state":
            return redirect('state_home')
        return redirect(next)
    else:
        return render(request, 'login.htm', {
            'app_name': settings.APP_NAME,
            'auth_failed': (auth_attempt_success is not None),
            'next': next,
            'login_type':login_type,
            'page':'login',
        })

@never_cache
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, _('Your password has been updated'))
            if user_is_land_manager(user):
                return redirect('state_home')
            if user_is_scout(user):
                return redirect('hms_home')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'change-password.htm', {
        'form': form,
        'page':'change-password'
    })

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
