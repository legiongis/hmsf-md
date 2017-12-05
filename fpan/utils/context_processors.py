from django.conf import settings
    
def user_type(request):
    state_groups = ['FL Aquatic Preserve','FL BAR','FL Forestry','FMSF','FWC','State Park']
    return {
        'user_is_state': request.user.groups.filter(name__in=state_groups).exists(),
        'user_is_scout': request.user.groups.filter(name='Scout').exists()
    }