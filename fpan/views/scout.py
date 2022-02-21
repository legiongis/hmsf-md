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
from fpan.models import Region
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
            s = form.save(commit=False)
            s.is_active = False
            s.username = newusername
            s.save()

            # now add some ScoutProfile info from the same form
            s.scoutprofile.region_choices.set(form.cleaned_data.get('region_choices', []))
            s.scoutprofile.zip_code = form.cleaned_data.get('zip_code')
            s.scoutprofile.background = form.cleaned_data.get('background')
            s.scoutprofile.relevant_experience = form.cleaned_data.get('relevant_experience')
            s.scoutprofile.interest_reason = form.cleaned_data.get('interest_reason')
            s.scoutprofile.site_interest_type = form.cleaned_data.get('site_interest_type')
            s.scoutprofile.save()

            current_site = get_current_site(request)
            baseurl = f"http://{current_site.domain}"
            if settings.HTTPS:
                baseurl = f"https://{current_site.domain}"
            msg_vars = {
                'user': s,
                'baseurl': baseurl,
                'uid': urlsafe_base64_encode(force_bytes(s.pk)),
                'token': account_activation_token.make_token(s),
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
                ma = ManagementArea.objects.get(pk=pk)
                site_regions.append(ma.name)

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
            "West Central": "FPAN West Central Region",
            "North Central": "FPAN North Central Region",
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
        'background': "Education/Occupation",
        'relevant_experience': "Relevant Experience",
        'interest_reason': "Interest Reason",
        'site_interest_type': "Site Types",
        'region_choices': "Regions",
        'date_joined': "Signup Date",
    }

    writer = csv.DictWriter(response, fieldnames=list(field_mapping.values()))
    writer.writeheader()
    for scout in Scout.objects.all():
        serialized = scout.serialize()
        translate_row = {field_mapping[k]: serialized[k] for k in serialized.keys()}        
        writer.writerow(translate_row)

    return response
