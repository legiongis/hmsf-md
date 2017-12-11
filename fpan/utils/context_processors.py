from django.conf import settings
from .accounts import check_state_access,check_scout_access
    
def user_type(request):
    return {
        'user_is_state': check_state_access(request.user),
        'user_is_scout': check_scout_access(request.user),
        'user_is_admin': request.user.is_superuser
    }