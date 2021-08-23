import csv
from datetime import datetime
from django.conf import settings
from django.shortcuts import render, HttpResponse
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string

from arches.app.utils.response import JSONResponse
from arches.app.models.tile import Tile
from arches.app.models.models import Node

from fpan.utils.permission_backend import user_is_anonymous
from fpan.utils.tokens import account_activation_token
from fpan.utils.accounts import generate_username
from hms.models import Scout, ScoutProfile, ManagementArea, ManagementAgency
from hms.forms import ScoutForm, ScoutProfileForm

def scout_signup(request):
    if request.method == "POST":
        form = ScoutForm(request.POST)
        if form.is_valid():
            firstname = form.cleaned_data.get('first_name')
            middleinitial = form.cleaned_data.get('middle_initial')
            lastname = form.cleaned_data.get('last_name')
            newusername = generate_username(firstname, middleinitial, lastname)
            user = form.save(commit=False)
            user.is_active = False
            user.username = newusername
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
                site_regions.append(ManagementArea.objects.get(pk=pk).name)

        ## this lookup is needed to translate between the names of the fpan.models.Region
        ## objects, which is what the ScoutProfile is related to, and the
        ## hms.models.ManagementArea objects, which is the content now stored in the 
        ## FPAN Region node. Ultimately, the ScoutProfile model should be related to
        ## ManagementArea and Region can be completely removed.
        lookup = {
            "Northwest": "FPAN Northwest Region",
            "Northeast": "FPAN Northeast Region",
            "Central": "FPAN Central Region",
            "East Central": "FPAN East Central Region",
            "Southwest": "FPAN Southwest Region",
            "Southeast": "FPAN Southeast Region",
        }

        ## as the scout list gets big this may need some optimizing!
        for scout in ScoutProfile.objects.all():
            for region_choice in scout.region_choices.all():
                if lookup[region_choice.name] in site_regions:
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
            'region_choices': [region.name for region in scout.region_choices.all()],
        })

    return JSONResponse(return_scouts)

@user_passes_test(lambda u: u.is_superuser)
def scout_list_download(request):

    csvname = datetime.now().strftime("HMS_all_scouts_%d-%m-%y.csv")

    # create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename={}'.format(csvname)

    ## create writer object
    writer = csv.writer(response)

    header_row = ['scoutid','first_name','last_name','email','street address',
                    'city','state','zip','phone','interests','region_choices',
                    'date_joined',
                 ]
    writer.writerow(header_row)

    rows = []
    all_scouts = Scout.objects.all()
    for scout in all_scouts:

        id = scout.username
        first_name = scout.first_name
        last_name = scout.last_name
        email = scout.email
        addr = scout.scoutprofile.street_address
        city = scout.scoutprofile.city
        state = scout.scoutprofile.state
        zip = scout.scoutprofile.zip_code
        phone = scout.scoutprofile.phone
        interests = ";".join(scout.scoutprofile.site_interest_type)
        regions = scout.scoutprofile.region_choices.all()
        region_names = ";".join([r.name for r in regions])
        joined = scout.date_joined.strftime("%Y-%m-%d")

        srow = [id,first_name,last_name,email,addr,city,state,zip,phone,
                    interests,region_names,joined]
        rows.append(srow)

    for row in rows:
        writer.writerow(row)

    return response

@user_passes_test(user_is_anonymous)
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
