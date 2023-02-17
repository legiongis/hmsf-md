from hms.permissions_backend import (
    user_is_land_manager,
    user_is_scout,
)
from site_theme.models import ProfileLink, ProfileContent

def profile_content(request):

    links = []
    content_obj = []

    if request.user.is_superuser:
        links += ProfileLink.objects.exclude(sortorder_admin=0).order_by('sortorder_admin')
        content_obj = ProfileContent.objects.exclude(sortorder_admin=0).order_by('sortorder_admin')
    elif user_is_land_manager(request.user):
        links += ProfileLink.objects.exclude(sortorder_landmanager=0).order_by('sortorder_landmanager')
        content_obj = ProfileContent.objects.exclude(sortorder_landmanager=0).order_by('sortorder_landmanager')
    elif user_is_scout(request.user):
        links += ProfileLink.objects.exclude(sortorder_scout=0).order_by('sortorder_scout')
        content_obj = ProfileContent.objects.exclude(sortorder_scout=0).order_by('sortorder_scout')

    if len(content_obj) > 0:
        content = content_obj[0].content
    else:
        content = None

    return {
        "profile_links": [i.serialize() for i in links],
        "profile_content": content,
    }