from django.http import HttpRequest
from ninja.security import HttpBearer

from core.models import Profile
from seo_blog_bot.utils import get_seo_blog_bot_logger

logger = get_seo_blog_bot_logger(__name__)


class APIKeyAuth(HttpBearer):
    """Authentication via API key in Bearer token"""

    def authenticate(self, request: HttpRequest, token: str) -> Profile | None:
        logger.info(
            "[Django Ninja Auth] API Request with token",
            token=token,
        )
        try:
            return Profile.objects.get(key=token)
        except Profile.DoesNotExist:
            logger.warning(f"Invalid API key: {token}")
            return None


class SessionAuth:
    """Authentication via Django session"""

    def authenticate(self, request: HttpRequest) -> Profile | None:
        if hasattr(request, "user") and request.user.is_authenticated:
            logger.info(
                "[Django Ninja Auth] API Request with authenticated user",
                user_id=request.user.id,
            )
            try:
                return request.user.profile
            except Profile.DoesNotExist:
                logger.warning(f"No profile for user: {request.user.id}")
                return None
        return None

    def __call__(self, request: HttpRequest):
        return self.authenticate(request)


class SuperuserAPIKeyAuth(HttpBearer):
    """Authentication via API key, but only for superusers"""

    def authenticate(self, request: HttpRequest, token: str) -> Profile | None:
        try:
            profile = Profile.objects.get(key=token)
            if profile.user.is_superuser:
                return profile
            logger.warning(
                "[Django Ninja Auth] Non-superuser attempted admin access",
                profile_id=profile.user.id,
            )
            return None
        except Profile.DoesNotExist:
            return None


api_key_auth = APIKeyAuth()
session_auth = SessionAuth()
superuser_api_auth = SuperuserAPIKeyAuth()
