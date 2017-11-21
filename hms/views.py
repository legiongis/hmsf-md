from django.shortcuts import render
from arches.app.utils.JSONResponse import JSONResponse
from .models import Scout, ScoutProfile
import json


def scouts_dropdown(request):
    results = ScoutProfile.objects.all()    
    result_list = []
    for scout in results:
        result_list.append({
            'id': scout.user_id,
            'scout': scout.user.username,
            'site_interest_type': scout.site_interest_type,
            'region_choices': [region.name for region in scout.region_choices.all()],
            })
    print(request)
    return JSONResponse(result_list)

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