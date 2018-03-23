from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache
from django.http import HttpResponse, Http404 
from django.core.urlresolvers import reverse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.core.mail import EmailMultiAlternatives
from django.utils.translation import ugettext as _
from hms.forms import ScoutForm, ScoutProfileForm
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string, get_template
from fpan.utils.tokens import account_activation_token
from fpan.utils.accounts import check_anonymous, check_duplicate_username, check_state_access, check_scout_access
from django.contrib.auth.models import User, Group
from arches.app.views.main import auth as arches_auth
from arches.app.models.system_settings import settings
from fpan.models import Region
from hms.models import Scout, ScoutProfile
from hms.views import scouts_dropdown
from django.contrib import messages
from arches.app.utils.JSONResponse import JSONResponse
import json


def index(request):
    scout_form = ScoutForm()
    return render(request, 'index.htm', {
        'main_script': 'index',
        'active_page': 'Home',
        'app_title': '{0} | HMS'.format(settings.APP_NAME),
        'copyright_text': settings.COPYRIGHT_TEXT,
        'copyright_year': settings.COPYRIGHT_YEAR,
        'scout_form': scout_form,
        'page':'index'
    })
    
# @user_passes_test(check_anonymous)
def hms_home(request):
    if request.method == "POST":
        scout_profile_form = ScoutProfileForm(
            request.POST,
            instance=request.user.scout.scoutprofile)
        if scout_profile_form.is_valid():
            scout_profile_form.save()
            messages.add_message(request, messages.INFO, 'Your profile has been updated.')
        else:
            messages.add_message(request, messages.ERROR, 'Form was invalid.')
        
        return render(request, "home-hms.htm", {
            'scout_profile': scout_profile_form,
            'page':'home-hms'})
        
    else:
        scout_profile_form = None
        try:
            scout_profile_form = ScoutProfileForm(instance=request.user.scout.scoutprofile)
        except Scout.DoesNotExist:
            pass

    return render(request, "home-hms.htm", {
        'scout_profile': scout_profile_form,
        'page':'home-hms'})
        
@user_passes_test(check_anonymous)
def scout_profile(request):
    if request.method == "POST":
        scout_profile_form = ScoutProfileForm(
            request.POST,
            instance=request.user.scout.scoutprofile)
        if scout_profile_form.is_valid():
            scout_profile_form.save()
            messages.add_message(request, messages.INFO, 'Your profile has been updated.')
        else:
            messages.add_message(request, messages.ERROR, 'Form was invalid.')

    else:
        scout_profile_form = ScoutProfileForm(instance=request.user.scout.scoutprofile)

    return render(request, "fpan/scout-profile.htm", {
        'scout_profile': scout_profile_form})

@user_passes_test(check_state_access)
def state_home(request):
    return render(request, 'home-state.htm', {'page':'home-state'})

@never_cache
def auth(request,login_type):

    if not login_type in ['hms','state','logout']:
        raise Http404("not found")
        
    if login_type == 'logout':
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

def scout_signup(request):
    if request.method == "POST":
        form = ScoutForm(request.POST)
        if form.is_valid():
            firstname = form.cleaned_data.get('first_name')
            middleinitial = form.cleaned_data.get('middle_initial')
            lastname = form.cleaned_data.get('last_name')
            user = form.save(commit=False)
            user.is_active = False
            user.username = check_duplicate_username(
                firstname[0].lower() 
                + middleinitial.lower() 
                + lastname.lower())

            user.save()
            current_site = get_current_site(request)
            msg_vars = {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user),
            }
            message_txt = render_to_string('email/account_activation_email.htm', msg_vars)
            message_html = render_to_string('email/account_activation_email_html.htm', msg_vars)
            subject_line = settings.EMAIL_SUBJECT_PREFIX + 'Activate your account.'
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = form.cleaned_data.get('email')
            email = EmailMultiAlternatives(subject_line,message_txt,from_email,to=[to_email])
            email.attach_alternative(message_html, "text/html")
            email.send()            
            return render(request,'email/please-confirm.htm')
    else:
        form = ScoutForm()

    return render(request, 'index.htm', {'scout_form': form})

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

def show_regions(request):
    regions = Region.objects.all()
    return JSONResponse(regions)

def server_error(request, template_name='500.html'):
    from django.template import RequestContext
    from django.http import HttpResponseServerError
    t = get_template(template_name)
    return HttpResponseServerError(t.render(RequestContext(request)))
    
@user_passes_test(lambda u: u.is_superuser)
def fpan_dashboard(request):
    scouts_unsorted = json.loads(scouts_dropdown(request).content)
    scouts = sorted(scouts_unsorted, key=lambda k: k['username']) 
    return render(request,'fpan-dashboard.htm',context={'scouts':scouts})
