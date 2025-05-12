import requests
from django.conf import settings
from django_q.tasks import async_task

from core.choices import ContentType, KeywordDataSource, ProjectPageType
from core.models import Competitor, Keyword, Project, ProjectKeyword, ProjectPage
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
    page_analyzed = False

    if created:
        project_page.get_page_content()
        page_analyzed = project_page.analyze_content()

    if project_page.type == ProjectPageType.PRICING and page_analyzed:
        async_task(project_page.create_new_pricing_strategy)

    return f"Analyzed {link} for {project.name}"


def schedule_project_page_analysis(project_id):
    project = Project.objects.get(id=project_id)
    project_links = project.get_a_list_of_links()

    count = 0
    for link in project_links:
        async_task(
            analyze_project_page,
            project_id,
            link,
        )
        count += 1

    return f"Scheduled analysis for {count} links"


def schedule_project_competitor_analysis(project_id):
    project = Project.objects.get(id=project_id)
    competitors = project.find_competitors()
    if competitors:
        competitors = project.get_and_save_list_of_competitors()
        for competitor in competitors:
            async_task(analyze_project_competitor, competitor.id)

    return f"Saved Competitors for {project.name}"


def analyze_project_competitor(competitor_id):
    competitor = Competitor.objects.get(id=competitor_id)
    got_content = competitor.get_page_content()

    if got_content:
        competitor.analyze_competitor()

    return f"Analyzed Competitor for {competitor.name}"


def process_project_keywords(project_id: int):
    """
    Processes proposed keywords for a project:
    1. Saves them to the Keyword model.
    2. Fetches metrics for each keyword.
    3. Associates keywords with the project.
    """
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        logger.error(f"[KeywordProcessing] Project with id {project_id} not found.")
        return f"Project with id {project_id} not found."

    if not project.proposed_keywords:
        logger.info(f"[KeywordProcessing] No proposed keywords for project {project.id} ({project.name}).")
        return f"No proposed keywords for project {project.name}."

    keyword_strings = [kw.strip() for kw in project.proposed_keywords.split(",") if kw.strip()]
    processed_count = 0
    failed_count = 0

    # Determine country code from project language, default to 'us'
    # Keywords Everywhere API uses 2-letter lowercase country codes.
    # Project language codes (e.g., 'en', 'es') fit this.
    country_code = "us"  # Default
    # if project.language and len(project.language) >= 2:
    #     country_code = project.language[:2].lower()

    for keyword_str in keyword_strings:
        try:
            keyword_obj, created = Keyword.objects.get_or_create(
                keyword_text=keyword_str, country=country_code, data_source=KeywordDataSource.GOOGLE_KEYWORD_PLANNER
            )
            if created:
                logger.info("[KeywordProcessing] Created new keyword", keyword_text=keyword_str)

            metrics_fetched = keyword_obj.fetch_and_update_metrics()
            if not metrics_fetched:
                logger.warning(
                    f"[KeywordProcessing] Failed to fetch metrics for keyword: {keyword_obj.id} ('{keyword_str}')."
                )

            # Associate with project
            ProjectKeyword.objects.get_or_create(project=project, keyword=keyword_obj)
            processed_count += 1
        except Exception as e:
            failed_count += 1
            logger.error(
                f"[KeywordProcessing] Error processing keyword '{keyword_str}' for project {project.id}.",
                error=str(e),
                project_id=project.id,
                keyword_text=keyword_str,
            )

    result_message = f"Keyword processing for project {project.name} (ID: {project.id}): Processed {processed_count} keywords, Failed: {failed_count}."
    logger.info(result_message)
    return result_message


def generate_blog_post_suggestions(project_id: int):
    project = Project.objects.get(id=project_id)
    project.generate_title_suggestions(content_type=ContentType.SHARING, num_titles=3)
    project.generate_title_suggestions(content_type=ContentType.SEO, num_titles=3)
    return "Blog post suggestions generated"
