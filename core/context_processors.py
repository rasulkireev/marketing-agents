from allauth.socialaccount.models import SocialApp
from django.conf import settings


def pro_subscription_status(request):
    """
    Adds a 'has_pro_subscription' variable to the context.
    This variable is True if the user has an active pro subscription, False otherwise.
    """
    if request.user.is_authenticated and hasattr(request.user, "profile"):
        return {"has_pro_subscription": request.user.profile.has_product_or_subscription}
    return {"has_pro_subscription": False}


def posthog_api_key(request):
    return {"posthog_api_key": settings.POSTHOG_API_KEY}


def github_social_auth_available(request):
    """
    Checks if GitHub social authentication is available.
    Returns True if GitHub is configured in SOCIALACCOUNT_PROVIDERS and
    a corresponding SocialApp exists in the database.
    """
    # Check if GitHub is configured in settings
    if "github" not in getattr(settings, "SOCIALACCOUNT_PROVIDERS", {}):
        return {"github_auth_available": False}

    # Check if SocialApp exists in database
    try:
        SocialApp.objects.get(provider="github")
        return {"github_auth_available": True}
    except SocialApp.DoesNotExist:
        return {"github_auth_available": False}
