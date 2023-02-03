from hms.permissions_backend import (
    user_is_land_manager,
    user_is_scout,
    generate_site_access_html,
)

def user_type(request):

    user_type = "anonymous"
    if request.user.is_superuser:
        user_type = "admin"
    elif user_is_land_manager(request.user):
        user_type = "landmanager"
    elif user_is_scout(request.user):
        user_type = "scout"
    return {
        'user_is_admin': request.user.is_superuser,
        'user_is_state': user_is_land_manager(request.user),
        'user_is_scout': user_is_scout(request.user),
        'user_type': user_type,
        'site_access_html': generate_site_access_html(request.user)
    }
