from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth import login, authenticate
from django.core.mail import EmailMessage
from .forms import ScoutSignupForm, ScoutProfileForm
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from .tokens import account_activation_token
from django.contrib.auth.models import User, Group
from arches.app.views.main import auth as arches_auth
from arches.app.models.system_settings import settings
from arches.app.utils.JSONResponse import JSONResponse
from fpan.models.region import Region
from fpan.models.scout import Scout


def index(request):
    scout_signup = ScoutSignupForm()
    return render(request, 'index.htm', {
        'main_script': 'index',
        'active_page': 'Home',
        'app_title': settings.APP_TITLE,
        'copyright_text': settings.COPYRIGHT_TEXT,
        'copyright_year': settings.COPYRIGHT_YEAR,
        'scout_signup': scout_signup
    })


def scout_signup(request):
    print("scout signup")
    if request.method == "POST":
        form = ScoutSignupForm(request.POST)
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
        form = ScoutSignupForm()

    return render(request, "account/register.htm", {'form': form})


def scout_profile(request):
    if request.method == "POST":
        reg_form = RegistrationForm(request.POST, instance=request.user)
        scout_form = ScoutProfileForm(request.POST)
        if reg_form.is_valid() and scout_form.is_valid():
            firstname = reg_form.cleaned_data.get('first_name')
            middleinitial = reg_form.cleaned_data.get('middle_initial')
            lastname = reg_form.cleaned_data.get('last_name')
            user = reg_form.save(commit=False)
            user.is_active = False
            user.username = check_duplicate_username(
                firstname[0].lower() 
                + middleinitial.lower() 
                + lastname.lower())

            user.save()
            scout_form.save()

            current_site = get_current_site(request)
            message = render_to_string('email/account_activation_email.htm', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user),
            })
            subject_line = 'Activate your account.'
            from_email = 'admin@localhost.tld'
            to_email = reg_form.cleaned_data.get('email')
            email = EmailMessage(subject_line, message, from_email, to=[to_email])
            email.send()            
            return HttpResponse('Please confirm your email address.')
    else:
        reg_form = RegistrationForm()
        scout_form = ScoutProfileForm()

    return render(request, "account/signup.htm", {
        'reg_form': reg_form,
        'scout_form': scout_form})


def activate(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
        print("User does not exist")
    if user is not None and account_activation_token.check_token(user, token):
        print(user)
        user.is_active = True
        scout_group = Group.objects.get(name="Scout")
        scout_group.user_set.add(user)
        user.save()
        user = authenticate(username=user.username, password=user.password)
        scout_form = ScoutProfileForm(request.POST)
        return render(request, "account/signup.htm", {'scout_form': scout_form})
        # return HttpResponse('Thank you for your email confirmation. Now you can login your account.' +
                            # '\n{}'.format(response))
    else:
        return HttpResponse('Activation link is invalid!')


def scouts_dropdown(request):
    results = User.objects.all()
    return JSONResponse(results)


def check_duplicate_username(newusername):
    inputname = newusername
    inc = 1
    while User.objects.filter(username=newusername).exists():
        if len(inputname) < len(newusername):
            offset = len(newusername) - len(inputname)
            inc = int(newusername[-offset:]) + 1
        newusername = inputname + '{}'.format(inc)
        print(newusername)
    return newusername


def show_regions(request):
    regions = Region.objects.all()
    return JSONResponse(regions)
