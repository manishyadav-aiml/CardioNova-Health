from django.conf import settings

from . import ml
from .models import Profile


def model_status(request):
    """Makes `model_info`, `is_doctor` and site details available in every template."""
    is_doctor = False
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        profile, _ = Profile.objects.get_or_create(user=user)
        is_doctor = profile.is_doctor or user.is_superuser
    return {"model_info": ml.model_info(), "is_doctor": is_doctor,
            "SITE_LAST_UPDATED": settings.SITE_LAST_UPDATED, "CONTACT_EMAIL": settings.CONTACT_EMAIL}
