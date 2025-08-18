from django.http import HttpRequest
from ninja.security import HttpBearer

from core.models import Profile
from seo_blog_bot.utils import get_seo_blog_bot_logger

logger = get_seo_blog_bot_logger(__name__)


class MultipleAuthSchema(HttpBearer):
    def authenticate(self, request: HttpRequest, token: str | None = None) -> Profile | None:
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
        logger.info(
            "[Django Ninja Auth] API Request",
            request=request.__dict__,
        )

        authorization = request.headers.get("Authorization") or request.headers.get(
            "authorization", ""
        )
        if authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]
            logger.info(
                "[Django Ninja Auth] Found Bearer token in headers",
                token=token,
                header_key_used="Authorization"
                if request.headers.get("Authorization")
                else "authorization",
            )
            return self.authenticate(request, token)

        if hasattr(request, "user") and request.user.is_authenticated:
            logger.info(
                "[Django Ninja Auth] No Bearer token found, falling back to session auth",
                user_authenticated=request.user.is_authenticated,
                available_headers=list(request.headers.keys()),
            )
            return self.authenticate(request)

        logger.warning(
            "[Django Ninja Auth] No authentication method found",
            available_headers=list(request.headers.keys()),
            user_authenticated=hasattr(request, "user") and request.user.is_authenticated,
        )
        return super().__call__(request)
