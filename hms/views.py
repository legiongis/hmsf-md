from django.shortcuts import render
from arches.app.utils.JSONResponse import JSONResponse
from .models import Scout
# Create your views here.


def scouts_dropdown(request):
    results = Scout.objects.all()
    return JSONResponse(results)
