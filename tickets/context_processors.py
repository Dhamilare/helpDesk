from .forms import UserProfileForm 
from .models import UserProfile

def profile_form_processor(request):
    profile_form = None
    if request.user.is_authenticated:
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        profile_form = UserProfileForm(instance=profile, user=request.user)
    return {'profile_form': profile_form}