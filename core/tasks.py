import json
from datetime import datetime, timedelta
from urllib.parse import unquote

import posthog
import pytz
import requests
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from django_q.tasks import async_task

from core.choices import ContentType, KeywordDataSource, ProjectPageType
from core.models import (
    AutoSubmissionSetting,
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
    profile_id: int, from_state: str, to_state: str, metadata: dict = None
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


def check_and_schedule_blog_posts():
    """
    Check each AutoSubmissionSetting and schedule blog posts for projects
    that need them based on their posting frequency and last post date.
    """
    try:
        # Get all active auto submission settings
        submission_settings = AutoSubmissionSetting.objects.all()
        
        results = []
        
        for setting in submission_settings:
            project = setting.project
            
            # Skip if project has no generated blog posts
            if not project.generated_blog_posts.exists():
                logger.info(
                    "No generated blog posts found for project",
                    project_id=project.id,
                    project_name=project.name
                )
                continue
            
            # Get the last posted blog post for this project
            last_posted_blog = project.generated_blog_posts.filter(
                posted=True
            ).order_by('-created_at').first()
            
            # Calculate when next post should be scheduled
            should_schedule, next_post_time = should_schedule_next_post(
                setting, last_posted_blog
            )
            
            if should_schedule:
                # Get the next unposted blog post
                next_blog_post = project.generated_blog_posts.filter(
                    posted=False
                ).order_by('created_at').first()
                
                if next_blog_post:
                    # Schedule the blog post
                    async_task(
                        "core.tasks.submit_scheduled_blog_post",
                        next_blog_post.id,
                        schedule=next_post_time,
                        group="Blog Post Submission"
                    )
                    
                    result = f"Scheduled blog post '{next_blog_post.post_title}' for {project.name} at {next_post_time}"
                    results.append(result)
                    logger.info(
                        "Scheduled blog post submission",
                        project_id=project.id,
                        project_name=project.name,
                        blog_post_id=next_blog_post.id,
                        blog_post_title=next_blog_post.post_title,
                        scheduled_time=next_post_time
                    )
                else:
                    logger.info(
                        "No unposted blog posts available for scheduling",
                        project_id=project.id,
                        project_name=project.name
                    )
            else:
                logger.info(
                    "No scheduling needed for project",
                    project_id=project.id,
                    project_name=project.name,
                    last_posted_date=last_posted_blog.created_at if last_posted_blog else None
                )
        
        return f"Blog post scheduling check completed. {len(results)} posts scheduled."
    
    except Exception as e:
        logger.error(
            "Error in check_and_schedule_blog_posts",
            error=str(e)
        )
        return f"Error checking and scheduling blog posts: {str(e)}"


def should_schedule_next_post(submission_setting, last_posted_blog):
    """
    Determine if a next blog post should be scheduled based on the submission setting
    and last posted blog post.
    
    Returns:
        tuple: (should_schedule: bool, next_post_time: datetime)
    """
    posts_per_month = submission_setting.posts_per_month
    preferred_timezone = submission_setting.preferred_timezone or 'UTC'
    preferred_time = submission_setting.preferred_time
    
    # Convert to the preferred timezone
    try:
        tz = pytz.timezone(preferred_timezone)
    except pytz.UnknownTimeZoneError:
        logger.warning(
            "Unknown timezone, using UTC",
            timezone=preferred_timezone,
            project_id=submission_setting.project.id
        )
        tz = pytz.UTC
    
    # Calculate the interval between posts (in days)
    days_between_posts = 30 / posts_per_month  # Approximate month as 30 days
    
    # Get current time in the preferred timezone
    current_time = timezone.now().astimezone(tz)
    
    # If no previous post, schedule immediately or at next preferred time
    if not last_posted_blog:
        if preferred_time:
            # Schedule for today at preferred time if it's in the future, otherwise tomorrow
            next_post_time = current_time.replace(
                hour=preferred_time.hour,
                minute=preferred_time.minute,
                second=0,
                microsecond=0
            )
            if next_post_time <= current_time:
                next_post_time += timedelta(days=1)
        else:
            # Schedule for immediate posting
            next_post_time = current_time + timedelta(minutes=5)
        
        return True, next_post_time
    
    # Calculate when the next post should be scheduled
    last_posted_time = last_posted_blog.created_at.astimezone(tz)
    next_scheduled_time = last_posted_time + timedelta(days=days_between_posts)
    
    # If preferred time is set, adjust to that time
    if preferred_time:
        next_scheduled_time = next_scheduled_time.replace(
            hour=preferred_time.hour,
            minute=preferred_time.minute,
            second=0,
            microsecond=0
        )
    
    # Check if enough time has passed
    if current_time >= next_scheduled_time:
        return True, next_scheduled_time
    
    return False, next_scheduled_time


def submit_scheduled_blog_post(blog_post_id):
    """
    Submit a scheduled blog post to its endpoint and mark it as posted.
    """
    try:
        blog_post = GeneratedBlogPost.objects.get(id=blog_post_id)
        
        # Submit the blog post
        success = blog_post.submit_blog_post_to_endpoint()
        
        if success:
            blog_post.posted = True
            blog_post.save(update_fields=['posted'])
            
            result = f"Successfully submitted blog post '{blog_post.post_title}' for {blog_post.project.name}"
            logger.info(
                "Blog post submitted successfully",
                project_id=blog_post.project.id,
                project_name=blog_post.project.name,
                blog_post_id=blog_post.id,
                blog_post_title=blog_post.post_title
            )
            return result
        else:
            logger.error(
                "Failed to submit blog post",
                project_id=blog_post.project.id,
                project_name=blog_post.project.name,
                blog_post_id=blog_post.id,
                blog_post_title=blog_post.post_title
            )
            return f"Failed to submit blog post '{blog_post.post_title}' for {blog_post.project.name}"
            
    except GeneratedBlogPost.DoesNotExist:
        logger.error(
            "Blog post not found for submission",
            blog_post_id=blog_post_id
        )
        return f"Blog post with ID {blog_post_id} not found"
    except Exception as e:
        logger.error(
            "Error submitting scheduled blog post",
            error=str(e),
            blog_post_id=blog_post_id
        )
        return f"Error submitting blog post: {str(e)}"
