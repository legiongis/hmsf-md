from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache
from django.http import HttpResponse, Http404
from django.core.urlresolvers import reverse
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.utils.translation import ugettext as _
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string, get_template

from arches.app.models.system_settings import settings

from fpan.utils.tokens import account_activation_token
from fpan.utils.accounts import check_state_access, check_scout_access

from hms.models import Scout
from hms.forms import ScoutForm, ScoutProfileForm

@never_cache
def auth(request,login_type):
    if not login_type in ['hms','state','logout']:
        raise Http404("not found")
        
    if login_type == 'logout':
        print "login type is logout"
        logout(request)
        return redirect('fpan_home')

    auth_attempt_success = None
    
    # POST request is taken to mean user is logging in
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        if user is not None and user.is_active:
            if login_type == "hms":
                if check_scout_access(user) or user.is_superuser:
                    login(request, user)
                    auth_attempt_success = True
                else:
                    auth_attempt_success = False
            elif login_type == "state":
                if check_state_access(user):
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
            if check_state_access(user):
                return redirect('state_home')
            if check_scout_access(user):
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