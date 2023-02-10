from django.conf.urls import include, url

urlpatterns = [
   url(r'^tinymce/', include('tinymce.urls')),
]