from django.http import HttpRequest
from ninja.security import HttpBearer

from core.models import Profile
from seo_blog_bot.utils import get_seo_blog_bot_logger

logger = get_seo_blog_bot_logger(__name__)


class MultipleAuthSchema(HttpBearer):
    def authenticate(self, request: HttpRequest, token: str | None = None) -> Profile | None:
        logger.info(
            "[Django Ninja Auth] API Request",
            request=request.__dict__,
            token=token,
        )

        # For API token authentication (when using the API directly)
        if token:
            logger.info(
                "[Django Ninja Auth] API Request with token",
                request=request.__dict__,
                token=token,
            )
            try:
                return Profile.objects.get(key=token)
            except Profile.DoesNotExist:
                return None

        # For session-based authentication (when using the web interface)
        if hasattr(request, "user") and request.user.is_authenticated:
            logger.info(
                "[Django Ninja Auth] API Request with user",
                request=request.__dict__,
                user=request.user.__dict__,
            )
            try:
                return request.user.profile
            except Profile.DoesNotExist:
                return None

        return None

    def __call__(self, request):
        # Override to make authentication optional for session-based requests
        if hasattr(request, "user") and request.user.is_authenticated:
            return self.authenticate(request)

        return super().__call__(request)
