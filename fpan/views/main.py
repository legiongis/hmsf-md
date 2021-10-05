import json
from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from django.template import RequestContext
from django.template.loader import get_template
from django.http import HttpResponseServerError
from django.contrib import messages
from arches.app.utils.response import JSONResponse
from arches.app.models.system_settings import settings
from arches.app.models.models import GraphModel
from fpan.utils.permission_backend import user_is_anonymous, user_is_land_manager
from fpan.models import Region
from hms.models import Scout, ScoutProfile
from hms.forms import ScoutForm, ScoutProfileForm

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

def show_regions(request):

    regions = Region.objects.all()
    return JSONResponse(regions)

def server_error(request, template_name='500.html'):

    t = get_template(template_name)
    return HttpResponseServerError(t.render(RequestContext(request).__dict__))
