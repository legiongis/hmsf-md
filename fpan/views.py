from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache
from django.http import HttpResponse, Http404 
from django.core.urlresolvers import reverse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import user_passes_test
from django.core.mail import EmailMessage
from hms.forms import ScoutForm, ScoutProfileForm
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from fpan.utils.tokens import account_activation_token
from fpan.utils.accounts import check_anonymous, check_duplicate_username
from django.contrib.auth.models import User, Group
from arches.app.views.main import auth as arches_auth
from arches.app.models.system_settings import settings
from fpan.models import Region
from hms.models import Scout, ScoutProfile
from django.contrib import messages
from arches.app.utils.JSONResponse import JSONResponse


def index(request):
    scout_form = ScoutForm()
    return render(request, 'index.htm', {
        'main_script': 'index',
        'active_page': 'Home',
        'app_title': '{0} | HMS'.format(settings.APP_NAME),
        'copyright_text': settings.COPYRIGHT_TEXT,
        'copyright_year': settings.COPYRIGHT_YEAR,
        'scout_form': scout_form
    })

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
            login(request, user)
            user.password = ''
            auth_attempt_success = True
        else:
            auth_attempt_success = False

    next = request.GET.get('next', reverse('home'))
    if auth_attempt_success:
        return redirect(next)
    else:
        if request.GET.get('logout', None) is not None:
            print "should be logging out now..."
            
            # need to redirect to 'auth' so that the user is set to anonymous via the middleware
            return redirect('fpan_home')
        else:
            if login_type == "hms":
                print "ok...."
                login_template = 'login-hms.htm'
            elif login_type == "state":
                login_template = 'login-state.htm'
            return render(request, login_template, {
                'app_name': settings.APP_NAME,
                'auth_failed': (auth_attempt_success is not None),
                'next': next
            })
    
@never_cache
def authhms(request):
    auth_attempt_success = None
    # POST request is taken to mean user is logging in
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        if user is not None and user.is_active:
            login(request, user)
            user.password = ''
            auth_attempt_success = True
        else:
            auth_attempt_success = False

    next = request.GET.get('next', reverse('home'))
    if auth_attempt_success:
        return redirect(next)
    else:
        if request.GET.get('logout', None) is not None:
            logout(request)
            # need to redirect to 'auth' so that the user is set to anonymous via the middleware
            return redirect('auth')
        else:
            return render(request, 'hms-login.htm', {
                'app_name': settings.APP_NAME,
                'auth_failed': (auth_attempt_success is not None),
                'next': next
            })

@never_cache
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, _('Your password has been updated'))
            return redirect('change_password')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'change_password.htm', {
        'form': form
    })

def scout_signup(request):
    print("scout signup")
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
            message = render_to_string('email/account_activation_email.htm', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user),
            })
            subject_line = 'Activate your account.'
            from_email = 'admin@localhost.tld'
            to_email = form.cleaned_data.get('email')
            email = EmailMessage(subject_line, message, from_email, to=[to_email])
            email.send()            
            return HttpResponse('Please confirm your email address.')
    else:
        form = ScoutForm()

    return render(request, "fpan/forms/_scout.htm", {'form': form})


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


def activate(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = Scout.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, Scout.DoesNotExist):
        user = None
        print("Scout does not exist")
    if user is not None and account_activation_token.check_token(user, token):
        print(user)
        user.is_active = True
        user.save()
        user = authenticate(username=user.username, password=user.password)
        scout_form = ScoutForm(instance=user)
        scout_profile_form = ScoutProfileForm()
        return redirect("scout_profile")
    else:
        return HttpResponse('Activation link is invalid!')


def show_regions(request):
    regions = Region.objects.all()
    return JSONResponse(regions)
