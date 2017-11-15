from django.shortcuts import render
from arches.app.utils.JSONResponse import JSONResponse
from .models import Scout, ScoutProfile
# Create your views here.


def scouts_dropdown(request):
    results = Scout.objects.all()
    return JSONResponse(results)

def scout_profile(request, username):
    return JSONResponse(ScoutProfile.objects.filter(user__username=username))
