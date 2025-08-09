import calendar
import json
import random
from urllib.parse import unquote

import posthog
import requests
from django.conf import settings
from django.utils import timezone
from django_q.tasks import async_task

from core.choices import ContentType, KeywordDataSource, ProjectPageType
from core.models import (
    BlogPostTitleSuggestion,
    Competitor,
    GeneratedBlogPost,
    Keyword,
    Profile,
    Project,
    ProjectKeyword,
    ProjectPage,
)
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
        logger.info(
            f"[KeywordProcessing] No proposed keywords for project {project.id} ({project.name})."
        )
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
                keyword_text=keyword_str,
                country=country_code,
                data_source=KeywordDataSource.GOOGLE_KEYWORD_PLANNER,
            )
            if created:
                logger.info(
                    "[KeywordProcessing] Created new keyword",
                    keyword_text=keyword_str,
                )

            metrics_fetched = keyword_obj.fetch_and_update_metrics()
            if not metrics_fetched:
                logger.warning(
                    "[KeywordProcessing] Failed to fetch metrics for keyword",
                    keyword_id=keyword_obj.id,
                    keyword_text=keyword_str,
                )

            # Associate with project
            ProjectKeyword.objects.get_or_create(project=project, keyword=keyword_obj)
            processed_count += 1
        except Exception as e:
            failed_count += 1
            logger.error(
                "[KeywordProcessing] Error processing keyword",
                error=str(e),
                project_id=project.id,
                keyword_text=keyword_str,
            )

    result_message = f"""
    Keyword processing for project {project.name} (ID: {project.id})
    Processed {processed_count} keywords
    Failed: {failed_count}
    """
    logger.info(result_message)
    return result_message


def generate_blog_post_suggestions(project_id: int):
    project = Project.objects.get(id=project_id)
    project.generate_title_suggestions(content_type=ContentType.SHARING, num_titles=3)
    project.generate_title_suggestions(content_type=ContentType.SEO, num_titles=3)
    return "Blog post suggestions generated"


def try_create_posthog_alias(profile_id: int, cookies: dict, source_function: str = None) -> str:
    base_log_data = {
        "profile_id": profile_id,
        "cookies": cookies,
        "source_function": source_function,
    }

    profile = Profile.objects.get(id=profile_id)
    email = profile.user.email

    base_log_data["email"] = email
    base_log_data["profile_id"] = profile_id

    posthog_cookie = cookies.get(f"ph_{settings.POSTHOG_API_KEY}_posthog")
    if not posthog_cookie:
        logger.warning("[Try Create Posthog Alias] No PostHog cookie found.", **base_log_data)
        return f"No PostHog cookie found for profile {profile_id}."
    base_log_data["posthog_cookie"] = posthog_cookie

    logger.info("[Try Create Posthog Alias] Setting PostHog alias", **base_log_data)

    cookie_dict = json.loads(unquote(posthog_cookie))
    frontend_distinct_id = cookie_dict.get("distinct_id")

    if frontend_distinct_id:
        posthog.alias(frontend_distinct_id, email)
        posthog.alias(frontend_distinct_id, str(profile_id))

    logger.info("[Try Create Posthog Alias] Set PostHog alias", **base_log_data)


def track_event(
    profile_id: int, event_name: str, properties: dict, source_function: str = None
) -> str:
    base_log_data = {
        "profile_id": profile_id,
        "event_name": event_name,
        "properties": properties,
        "source_function": source_function,
    }

    try:
        profile = Profile.objects.get(id=profile_id)
    except Profile.DoesNotExist:
        logger.error("[TrackEvent] Profile not found.", **base_log_data)
        return f"Profile with id {profile_id} not found."

    posthog.capture(
        profile.user.email,
        event=event_name,
        properties={
            "profile_id": profile.id,
            "email": profile.user.email,
            "current_state": profile.state,
            **properties,
        },
    )

    logger.info("[TrackEvent] Tracked event", **base_log_data)

    return f"Tracked event {event_name} for profile {profile_id}"


def track_state_change(
    profile_id: int,
    from_state: str,
    to_state: str,
    metadata: dict = None,
) -> None:
    from core.models import Profile, ProfileStateTransition

    base_log_data = {
        "profile_id": profile_id,
        "from_state": from_state,
        "to_state": to_state,
        "metadata": metadata,
    }

    try:
        profile = Profile.objects.get(id=profile_id)
    except Profile.DoesNotExist:
        logger.error("[TrackStateChange] Profile not found.", **base_log_data)
        return f"Profile with id {profile_id} not found."

    if from_state != to_state:
        logger.info("[TrackStateChange] Tracking state change", **base_log_data)
        ProfileStateTransition.objects.create(
            profile=profile,
            from_state=from_state,
            to_state=to_state,
            backup_profile_id=profile_id,
            metadata=metadata,
        )
        profile.state = to_state
        profile.save(update_fields=["state"])

    return f"Tracked state change from {from_state} to {to_state} for profile {profile_id}"


def schedule_blog_post_posting():
    projects = Project.objects.filter(enable_automatic_post_submission=True)
    for project in projects:
        if not project.has_auto_submission_setting:
            continue

        now = timezone.now()
        last_post_date = project.last_posted_blog_post.date_posted
        time_since_last_post_in_seconds = (now - last_post_date).total_seconds()

        days_in_month = calendar.monthrange(now.year, now.month)[1]
        time_between_posts_in_seconds = int(
            days_in_month
            * (24 * 60 * 60)
            / project.auto_submission_settings.latest("created_at").posts_per_month
        )

        if time_since_last_post_in_seconds > time_between_posts_in_seconds:
            async_task(generate_and_post_blog_post, project.id)


def generate_and_post_blog_post(project_id: int):
    project = Project.objects.get(id=project_id)

    # first see if there are generated blog posts that are not posted yet
    blog_post_to_post = GeneratedBlogPost.objects.filter(project=project, posted=False)

    # then see if there are blog post title suggestions without generated blog posts
    if not blog_post_to_post:
        ungenerated_blog_post_suggestions = BlogPostTitleSuggestion.objects.filter(
            project=project, generated_blog_posts__isnull=True
        )
        if ungenerated_blog_post_suggestions:
            ungenerated_blog_post_suggestion = ungenerated_blog_post_suggestions.first()
            blog_post_to_post = ungenerated_blog_post_suggestion.generate_content(
                content_type=ungenerated_blog_post_suggestion.content_type
            )

    # if neither, create a new blog post title suggestion, generate the blog post
    if not blog_post_to_post:
        content_type = random.choice([choice[0] for choice in ContentType.choices])
        suggestions = project.generate_title_suggestions(content_type=content_type, num_titles=1)
        blog_post_to_post = suggestions[0].generate_content(
            content_type=suggestions[0].content_type
        )

    # once you have the generated blog post, submit it to the endpoint
    if blog_post_to_post:
        result = blog_post_to_post.submit_blog_post_to_endpoint()
        if result is True:
            blog_post_to_post.posted = True
            blog_post_to_post.date_posted = timezone.now()
            blog_post_to_post.save(update_fields=["posted", "date_posted"])
            return f"Posted blog post for {project.name}"
        else:
            return f"Failed to post blog post for {project.name}."
    else:
        return f"No blog post to post for {project.name}."
