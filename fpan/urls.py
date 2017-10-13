from django.conf.urls import include, url
from django.contrib import admin
from fpan.account import views

urlpatterns = [
    url(r'^register/$', views.register, name='register'),
    url(r'^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', views.activate, name='activate'),
    url(r'^', include('arches.urls')),
    url(r'^admin/', admin.site.urls),
]
