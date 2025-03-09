import requests
from django.conf import settings
from django_q.tasks import async_task

from core.models import Project, ProjectPage
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


def analyze_project_page(project_id: int, link: str):
    project = Project.objects.get(id=project_id)
    project_page, created = ProjectPage.objects.get_or_create(project=project, url=link)
    if created:
        project_page.get_page_content()
        project_page.analyze_content()

    return f"Analyzed {link} for {project.name}"


def schedule_project_page_analysis(project_id):
    project = Project.objects.get(id=project_id)
    project_links = project.get_a_list_of_links()

    logger.info(
        "[Schedule Project Pages Analysis] Got Project Links",
        number_of_links=len(project_links),
        links=project_links,
    )

    logger.info(
        "[Schedule Project Page Analysis] Scheduling analysis for links",
        project_name=project.name,
        project_id=project.id,
        links=project_links,
        count=len(project_links),
    )

    count = 0
    for link in project_links:
        async_task(
            analyze_project_page,
            project_id,
            link,
        )
        count += 1

    return f"Scheduled analysis for {count} links"
