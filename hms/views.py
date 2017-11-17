from django.shortcuts import render
from arches.app.utils.JSONResponse import JSONResponse
from .models import Scout, ScoutProfile
# Create your views here.


def scouts_dropdown(request):
    results = ScoutProfile.objects.select_related('user__username').prefetch_related('region_choices__name') 
    print(results.values('user__username', 'site_interest_type', 'region_choices__name')) 
    # print(results[0].get_region_choices__name) 
    return JSONResponse(results.values('user__username', 'site_interest_type', 'region_choices__name'))

def scout_profile(request, username):
    return JSONResponse(ScoutProfile.objects.filter(user__username=username))

# (<django.db.models.fields.AutoField: id>, 
# <django.db.models.fields.related.OneToOneField: user>, 
# <django.db.models.fields.CharField: street_address>, 
# <django.db.models.fields.CharField: city>, 
# <django.db.models.fields.CharField: state>, 
# <django.db.models.fields.CharField: zip_code>, 
# <django.db.models.fields.CharField: phone>, 
# <django.db.models.fields.TextField: background>, 
# <django.db.models.fields.TextField: relevant_experience>, 
# <django.db.models.fields.TextField: interest_reason>, 
# <django.contrib.postgres.fields.array.ArrayField: site_interest_type>, 
# <django.db.models.fields.BooleanField: ethics_agreement>, 
# <django.db.models.fields.related.ManyToManyField: region_choices>)