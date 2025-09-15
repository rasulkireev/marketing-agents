from allauth.socialaccount.models import SocialApp
from django.conf import settings

from tuxseo.utils import get_tuxseo_logger

logger = get_tuxseo_logger(__name__)


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


def available_social_providers(request):
    """
    Checks which social authentication providers are available.
    Returns a list of provider names that are both configured in
    SOCIALACCOUNT_PROVIDERS and have corresponding SocialApp entries in the database.
    """
    available_providers = []

    # Get configured providers from settings
    configured_providers = getattr(settings, "SOCIALACCOUNT_PROVIDERS", {})

    logger.debug("Configured providers", configured_providers=configured_providers)

    # Check each configured provider for a corresponding SocialApp
    for provider_name in configured_providers.keys():
        try:
            SocialApp.objects.get(provider=provider_name)
            available_providers.append(provider_name)
        except SocialApp.DoesNotExist:
            continue

    return {
        "available_social_providers": available_providers,
        "has_social_providers": len(available_providers) > 0,
    }
