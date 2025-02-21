import requests
from django.conf import settings

from core.models import Project
from seo_blog_bot.utils import get_seo_blog_bot_logger

logger = get_seo_blog_bot_logger(__name__)


def add_email_to_buttondown(email, tag):
    data = {
        "email_address": str(email),
        "metadata": {"source": tag},
        "tags": [tag],
        "referrer_url": "https://seo_blog_bot.app",
        "subscriber_type": "regular",
    }

    r = requests.post(
        "https://api.buttondown.email/v1/subscribers",
        headers={"Authorization": f"Token {settings.BUTTONDOWN_API_KEY}"},
        json=data,
    )

    return r.json()


def get_page_content(project_id):
    project = Project.objects.get(id=project_id)
    got_content = project.get_page_content()

    return got_content
