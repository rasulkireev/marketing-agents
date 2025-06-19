import json
from urllib.parse import unquote

from django.conf import settings

from seo_blog_bot.settings import posthog
from seo_blog_bot.utils import get_seo_blog_bot_logger

logger = get_seo_blog_bot_logger(__name__)


class PostHogMiddleware:
    def __init__(self, get_response):
        logger.debug("PostHogMiddleware initialized")
        self.get_response = get_response

    def __call__(self, request):
        logger.debug("PostHogMiddleware called")
        try:
            if request.user.is_authenticated and hasattr(request.user, "email"):
                posthog_cookie = request.COOKIES.get(f"ph_{settings.POSTHOG_API_KEY}_posthog")
                if posthog_cookie:
                    logger.debug("PostHog cookie found", posthog_cookie=posthog_cookie)
                    try:
                        cookie_dict = json.loads(unquote(posthog_cookie))
                        frontend_distinct_id = cookie_dict.get("distinct_id")

                        # If frontend distinct_id exists and is different from user email, alias them
                        if frontend_distinct_id and frontend_distinct_id != request.user.email:
                            logger.debug(
                                "Aliasing PostHog distinct_id with user email",
                                distinct_id=frontend_distinct_id,
                                email=request.user.email,
                            )
                            posthog.alias(frontend_distinct_id, request.user.email)

                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(
                            "Failed to parse PostHog cookie",
                            exc_info=e,
                            error=str(e),
                            request=request,
                        )
                else:
                    logger.debug("No PostHog cookie found", request=request)
        except Exception as e:
            logger.error(
                "PostHog middleware error",
                exc_info=e,
                error=str(e),
                request=request,
            )

        response = self.get_response(request)
        return response
