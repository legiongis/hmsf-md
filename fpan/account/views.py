from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth import login, authenticate
from django.core.mail import EmailMessage
from .forms import ScoutRegistrationForm
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from .tokens import account_activation_token
from django.contrib.auth.models import User
from arches.app.views.main import auth as arches_auth
from arches.app.models.system_settings import settings


def register(request):
    if request.method == "POST":
        form = ScoutRegistrationForm(request.POST)
        if form.is_valid():
            firstname = form.cleaned_data.get('first_name')
            middleinitial = form.cleaned_data.get('middle_initial')
            lastname = form.cleaned_data.get('last_name')
            user = form.save(commit=False)
            user.is_active = False
            user.username = check_duplicate_username(firstname[0].lower() + middleinitial.lower() + lastname.lower())
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
        form = ScoutRegistrationForm()

    return render(request, "account/register.htm", {'form': form})


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
        user.save()
        response = arches_auth(request)
        print(response)
        # return render(request, 'login.htm', {
        #     'app_name': settings.APP_NAME,
        #     'auth_failed': 1,
        #     'next': 'home'
        # })
        # user = authenticate(username=user.username, password=user.password)
        # login(request, user)
        # return redirect('home')
        return HttpResponse('Thank you for your email confirmation. Now you can login your account.' +
                            '\n{}'.format(response))
    else:
        return HttpResponse('Activation link is invalid!')


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
