import unicodecsv
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
from arches.app.models.resource import Resource
from arches.app.models.tile import Tile
from arches.app.models.models import Node, Value

from fpan.models import Region
from fpan.utils.accounts import check_anonymous
from fpan.utils.tokens import account_activation_token
from fpan.utils.fpan_account_utils import check_duplicate_username
from hms.models import Scout, ScoutProfile
from hms.forms import ScoutForm, ScoutProfileForm

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

def scouts_dropdown(request):
    resourceid = request.GET.get('resourceid', None)

    ## get all scouts right off the bat
    all_scouts = ScoutProfile.objects.all()
    return_scouts = []

    ## this should be improved with a big refactoring of this view. DRY...
    if not resourceid:
        for scout in all_scouts:
            display_name = scout.user.username + " | " + ", ".join(scout.site_interest_type)
            return_scouts.append({
                'id': scout.user_id,
                'username': scout.user.username,
                'display_name': display_name,
                'site_interest_type': scout.site_interest_type,
                'region_choices': [region.name for region in scout.region_choices.all()],
            })
        return JSONResponse(return_scouts)

    ## use the resource instance id to find the graphid
    resource = Resource.objects.get(resourceinstanceid=resourceid)
    graphid = resource.graph_id

    ## use the graphid to figure out which HMS-Region node is the one in
    ## this particular resource model
    region_node = Node.objects.get(name="HMS-Region",graph_id=graphid)

    ## get the tiles for this resource instance and specifically those
    ## saved for the HMS-Region node
    tiles = Tile.objects.filter(resourceinstance=resourceid,nodegroup_id=region_node.nodegroup_id)

    ## iterate through all of the tiles (though in this case there should
    ## only be one) and make a list of the individual values stored for the 
    ## region node
    region_val_uuids = []
    for t in tiles:
        for tt in t.data[str(region_node.nodeid)]:
            region_val_uuids.append(tt)

    ## iterate through the values retrieved (which are UUIDs for Value
    ## instances of preflabels) and turn the values which are the actual
    ## labels of the HMS-Region node into Region objects and make a list
    regions = []
    for t in region_val_uuids:
        v = Value.objects.get(valueid=t)
        regions.append(Region.objects.get(name=v.value))

    ## as the scout list gets big this may need some optimizing!
    for scout in all_scouts:
        for region in regions:
            if region in scout.region_choices.all():
                display_name = scout.user.username + " | " + ", ".join(scout.site_interest_type)
                obj = {
                    'id': scout.user_id,
                    'username': scout.user.username,
                    'display_name': display_name,
                    'site_interest_type': scout.site_interest_type,
                    'region_choices': [region.name for region in scout.region_choices.all()],
                }
                if not obj in return_scouts:
                    return_scouts.append(obj)

    return JSONResponse(return_scouts)

@user_passes_test(lambda u: u.is_superuser)
def scout_list_download(request):

    csvname = datetime.now().strftime("HMS all scouts %d-%m-%y.csv")

    # create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename={}'.format(csvname)

    ## create writer object
    writer = unicodecsv.writer(response)

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
