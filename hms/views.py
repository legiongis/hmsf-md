import csv
import logging
from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import user_passes_test
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpResponseServerError
from django.shortcuts import render, redirect, HttpResponse
from django.template import RequestContext
from django.template.loader import render_to_string, get_template
from django.utils.encoding import force_text
from django.utils.http import urlsafe_base64_decode
from django.utils.translation import ugettext as _
from django.urls import reverse
from django.views.generic import View

from arches.app.utils.response import JSONResponse
from arches.app.models.tile import Tile
from arches.app.models.models import Node
from arches.app.models.system_settings import settings

from hms.forms import ScoutForm, ScoutProfileForm
from hms.models import Scout, ScoutProfile, ManagementArea
from hms.permissions_backend import user_is_land_manager, user_is_scout
from hms.utils import account_activation_token, create_scout_from_valid_form


logger = logging.getLogger(__name__)

def index(request):
    scout_form = ScoutForm()
    return render(request, 'index.htm', {
        'main_script': 'index',
        'active_page': 'Home',
        'app_title': '{0} | HMS'.format(settings.APP_NAME),
        'scout_form': scout_form,
        'page':'index'
    })

def about(request):
    return render(request, 'about.htm', {
        'main_script': 'about',
        'active_page': 'About',
        'app_title': '{0} | HMS'.format(settings.APP_NAME),
        'page':'about'
    })

@user_passes_test(user_is_scout)
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

        return redirect(reverse('user_profile_manager'))

    else:
        scout_profile_form = None
        try:
            scout_profile_form = ScoutProfileForm(instance=request.user.scout.scoutprofile)
        except Scout.DoesNotExist:
            pass
        return render(request, "home-hms.htm", {
            'scout_profile': scout_profile_form,
            'page':'home-hms'})

def server_error(request, template_name='500.html'):

    t = get_template(template_name)
    return HttpResponseServerError(t.render(RequestContext(request).__dict__))


class LoginView(View):
    def get(self, request):

        login_type = request.GET.get("t", "landmanager")
        if request.GET.get("logout", None) is not None:

            try:
                user = request.user
            except Exception as e:
                logger.warn(e)
                return redirect(f"/")

            if user_is_scout(user):
                login_type = "scout"
            # send land managers and admin back to the landmanager login
            else:
                login_type = "landmanager"

            logger.info(f"logging out: {user.username} | redirect to /auth/ should follow")
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

                # set next redirect if not previously set
                if next is None:
                    next = request.POST.get("next", reverse("user_profile_manager"))

                return redirect(next)

        return render(request, "login.htm", {
            "auth_failed": True,
            "next": next,
            "login_type": login_type
        }, status=401)

def login_patch(request, login_type):
    return redirect(f"/auth/?t={login_type}")

def activate_page(request, uidb64, token):
    
    return render(request, "hms/email/activation_page.htm", {
        "activation_link": f"/activate/?uidb64={uidb64}&token={token}",
    })

def activate(request):

    uidb64 = request.GET.get("uidb64")
    token = request.GET.get("token")
    if all([uidb64, token]):
        try:
            uid = force_text(urlsafe_base64_decode(uidb64))
            logger.debug(f"activate user: {uid}")
            user = Scout.objects.get(pk=uid)
        except(TypeError, ValueError, OverflowError, Scout.DoesNotExist) as e:
            logger.debug(f"error during account activation: {e}")
            return redirect("/auth/?t=scout")
        valid_token = account_activation_token.check_token(user, token)
        if not valid_token:
            logger.debug(f"token is invalid (user already activated??)")
        if user is not None and valid_token:
            user.is_active = True
            user.save()
            logger.debug(f"user set to active: {user}")
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            return redirect(reverse("user_profile_manager"))

    return redirect("/auth/?t=scout")

def scout_signup(request):
    if request.method == "POST":
        form = ScoutForm(request.POST)
        if form.is_valid():
            scout, encoded_uid, token = create_scout_from_valid_form(form)

            current_site = get_current_site(request)
            baseurl = f"http://{current_site.domain}"
            if settings.HTTPS:
                baseurl = f"https://{current_site.domain}"
            msg_vars = {
                'user': scout,
                'baseurl': baseurl,
                'uid': encoded_uid,
                'token': token,
            }
            message_txt = render_to_string('hms/email/account_activation_email.htm', msg_vars)
            message_html = render_to_string('hms/email/account_activation_email_html.htm', msg_vars)
            subject_line = settings.EMAIL_SUBJECT_PREFIX + 'Activate your account.'
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = form.cleaned_data.get('email')
            email = EmailMultiAlternatives(subject_line,message_txt,from_email,to=[to_email])
            email.attach_alternative(message_html, "text/html")
            email.send()
            return render(request,'hms/email/please-confirm.htm')
    else:
        form = ScoutForm()

    return render(request, 'index.htm', {'scout_form': form})

def scouts_dropdown(request):
    resourceid = request.GET.get('resourceid', None)

    ## get all scouts right off the bat
    if resourceid is None:
        matched_scouts = ScoutProfile.objects.all()
    else:
        matched_scouts = []

        site_regions = []
        n = Node.objects.get(name="FPAN Region", graph__name="Archaeological Site")
        region_tiles = Tile.objects.filter(resourceinstance=resourceid, nodegroup=n.nodegroup)
        for t in region_tiles:
            for pk in t.data[str(n.nodeid)]:
                ma = ManagementArea.objects.get(pk=pk)
                site_regions.append(ma.name)

        ## as the scout list gets big this may need some optimizing!
        for scout in ScoutProfile.objects.all():
            for region in scout.fpan_regions.all():
                if region.name in site_regions:
                    matched_scouts.append(scout)

    # iterate scouts and create a list of objects to return for the dropdown
    return_scouts = []
    for scout in matched_scouts:
        display_name = f"{scout.user.username} | {', '.join(scout.site_interest_type)}"
        if scout.site_access_mode == "FULL":
            display_name += " | already has FULL access to sites"
        return_scouts.append({
            'id': scout.user_id,
            'username': scout.user.username,
            'display_name': display_name,
            'site_interest_type': scout.site_interest_type,
            'fpan_regions': [region.name for region in scout.fpan_regions.all()],
        })

    return JSONResponse(return_scouts)

@user_passes_test(lambda u: u.is_superuser)
def scout_list_download(request):

    csvname = datetime.now().strftime("HMS_all_scouts_%d-%m-%y.csv")

    # create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename={}'.format(csvname)

    # the keys here must match those returned by the Scout().serialize() method
    field_mapping = {
        'username': "Scout ID",
        'first_name': "First Name",
        'last_name': "Last Name",
        'email': "Email",
        'street_address': "Street Address",
        'city': "City",
        'state': "State",
        'zip_code': "Zip Code",
        'phone': "Phone",
        'site_interest_type': "Site Types",
        'fpan_regions': "Regions",
        'date_joined': "Signup Date",
        'background': "Education/Occupation",
        'relevant_experience': "Relevant Experience",
        'interest_reason': "Interest Reasons",
    }

    writer = csv.DictWriter(response, fieldnames=list(field_mapping.values()))
    writer.writeheader()
    for scout in Scout.objects.all():
        serialized = scout.serialize()
        translate_row = {field_mapping[k]: serialized[k] for k in serialized.keys()}        
        writer.writerow(translate_row)

    return response
