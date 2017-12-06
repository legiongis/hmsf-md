from django.conf import settings
    
def user_type(request):
    state_groups = ['FL Aquatic Preserve','FL BAR','FL Forestry','FMSF','FWC','State Park']
    state_user = request.user.groups.filter(name__in=state_groups).exists()
    if request.user.is_superuser:
        state_user = False
    return {
        'user_is_state': state_user,
        'user_is_scout': request.user.groups.filter(name='Scout').exists(),
        'user_is_admin': request.user.is_superuser
    }