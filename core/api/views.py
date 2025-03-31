from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django_q.tasks import async_task
from ninja import NinjaAPI

from core.api.auth import MultipleAuthSchema
from core.api.schemas import (
    AddCompetitorIn,
    AddPricingPageIn,
    CompetitorAnalysisOut,
    CreatePricingStrategyIn,
    GeneratedContentOut,
    GenerateTitleSuggestionOut,
    GenerateTitleSuggestionsIn,
    GenerateTitleSuggestionsOut,
    ProjectScanIn,
    ProjectScanOut,
    SubmitFeedbackIn,
    UpdateTitleScoreIn,
)
from core.choices import ContentType, ProjectPageType
from core.models import BlogPostTitleSuggestion, Competitor, Feedback, Project, ProjectPage
from core.tasks import schedule_project_competitor_analysis, schedule_project_page_analysis
from seo_blog_bot.utils import get_seo_blog_bot_logger

logger = get_seo_blog_bot_logger(__name__)

api = NinjaAPI(auth=MultipleAuthSchema(), csrf=True, version="1.0.0")


@api.post("/scan", response=ProjectScanOut)
def scan_project(request: HttpRequest, data: ProjectScanIn):
    profile = request.auth

    project = Project.objects.filter(profile=profile, url=data.url).first()
    if project:
        return {
            "status": "success",
            "project_id": project.id,
            "has_details": bool(project.name),
            "has_suggestions": project.blog_post_title_suggestions.exists(),
        }

    if Project.objects.filter(url=data.url).exists():
        return {
            "status": "error",
            "message": "Project already exists",
        }

    try:
        project = Project.objects.create(profile=profile, url=data.url)
        got_content = project.get_page_content()
        analyzed_project = project.analyze_content()

        if got_content and analyzed_project:
            async_task(schedule_project_page_analysis, project.id)
            async_task(schedule_project_competitor_analysis, project.id, timeout=180)
            return {
                "status": "success",
                "project_id": project.id,
                "name": project.name,
                "type": project.get_type_display(),
                "url": project.url,
                "summary": project.summary,
            }
        else:
            logger.error(
                "[Scan Project] Project has no content",
                got_content=got_content,
                analyzed_project=analyzed_project,
                project_id=project.id if project else None,
                url=data.url,
            )
            if project:
                project.delete()
            return {
                "status": "error",
                "message": f"Failed to {'get page content' if not got_content else 'analyze project'}.",
            }

    except Exception as e:
        logger.error(
            "[Scan Project] Failed to scan project",
            error=str(e),
            exc_info=True,
            project_id=project.id if project else None,
            url=data.url,
        )
        if project:
            project.delete()
        return {
            "status": "error",
            "message": str(e),
        }


@api.post("/generate-title-suggestions", response=GenerateTitleSuggestionsOut)
def generate_title_suggestions(request: HttpRequest, data: GenerateTitleSuggestionsIn):
    profile = request.auth
    project = get_object_or_404(Project, id=data.project_id, profile=profile)

    try:
        content_type = ContentType[data.content_type]
    except KeyError:
        return {"suggestions": [], "status": "error", "message": f"Invalid content type: {data.content_type}"}

    if profile.number_of_title_suggestions + data.num_titles >= 20 and not profile.has_active_subscription:
        return {
            "suggestions": [],
            "status": "error",
            "message": "Title generation limit reached. Consider <a class='underline' href='/pricing'>upgrading</a>?",
        }

    suggestions = project.generate_title_suggestions(content_type=content_type, num_titles=data.num_titles)

    return {"suggestions": suggestions, "status": "success", "message": ""}


@api.post("/generate-title-from-idea", response=GenerateTitleSuggestionOut)
def generate_title_from_idea(request: HttpRequest, data: GenerateTitleSuggestionsIn):
    profile = request.auth
    project = get_object_or_404(Project, id=data.project_id, profile=profile)

    if profile.reached_title_generation_limit:
        return {
            "status": "error",
            "message": "Title generation limit reached. Consider <a class='underline' href='/pricing'>upgrading</a>?",
        }

    try:
        try:
            content_type = ContentType[data.content_type]
        except KeyError:
            return {"status": "error", "message": f"Invalid content type: {data.content_type}"}

        suggestions = project.generate_title_suggestions(
            content_type=content_type, num_titles=1, user_prompt=data.user_prompt
        )

        if not suggestions:
            return {"status": "error", "message": "No suggestions were generated"}

        suggestion = suggestions[0]

        return {
            "status": "success",
            "suggestion": {
                "id": suggestion.id,
                "title": suggestion.title,
                "description": suggestion.description,
                "category": suggestion.category,
                "target_keywords": suggestion.target_keywords,
                "suggested_meta_description": suggestion.suggested_meta_description,
                "content_type": suggestion.content_type,
            },
        }

    except Exception as e:
        logger.error(
            "Failed to generate title from idea", error=str(e), project_id=project.id, user_prompt=data.user_prompt
        )
        raise ValueError(f"Failed to generate title: {str(e)}")


@api.post("/generate-blog-content/{suggestion_id}", response=GeneratedContentOut)
def generate_blog_content(request: HttpRequest, suggestion_id: int):
    profile = request.auth
    suggestion = get_object_or_404(BlogPostTitleSuggestion, id=suggestion_id, project__profile=profile)

    if profile.reached_content_generation_limit:
        return {
            "status": "error",
            "message": "Content generation limit reached. Consider <a class='underline' href='/pricing'>upgrading</a>?",
        }

    try:
        blog_post = suggestion.generate_content(content_type=suggestion.content_type)

        if not blog_post or not blog_post.content:
            return {"status": "error", "message": "Failed to generate content. Please try again."}

        return {
            "status": "success",
            "content": blog_post.content,
            "slug": blog_post.slug,
            "tags": blog_post.tags,
            "description": blog_post.description,
        }

    except ValueError as e:
        logger.error(
            "Failed to generate blog content", error=str(e), suggestion_id=suggestion_id, profile_id=profile.id
        )
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(
            "Unexpected error generating blog content",
            error=str(e),
            exc_info=True,
            suggestion_id=suggestion_id,
            profile_id=profile.id,
        )
        return {"status": "error", "message": "An unexpected error occurred. Please try again later."}


@api.post("/projects/{project_id}/update", response={200: dict})
def update_project(request: HttpRequest, project_id: int):
    profile = request.auth
    logger.info("Updating project", project_id=project_id, profile_id=profile.id)
    project = get_object_or_404(Project, id=project_id, profile=profile)

    # Update project fields from form data
    project.key_features = request.POST.get("key_features", "")
    project.target_audience_summary = request.POST.get("target_audience_summary", "")
    project.pain_points = request.POST.get("pain_points", "")
    project.product_usage = request.POST.get("product_usage", "")
    project.links = request.POST.get("links", "")
    project.blog_theme = request.POST.get("blog_theme", "")
    project.founders = request.POST.get("founders", "")
    project.language = request.POST.get("language", "")

    project.save()

    return {"status": "success"}


@api.post("/update-title-score/{suggestion_id}", response={200: dict})
def update_title_score(request: HttpRequest, suggestion_id: int, data: UpdateTitleScoreIn):
    profile = request.auth
    suggestion = get_object_or_404(BlogPostTitleSuggestion, id=suggestion_id, project__profile=profile)

    if data.score not in [-1, 0, 1]:
        return {"status": "error", "message": "Invalid score value. Must be -1, 0, or 1"}

    try:
        suggestion.user_score = data.score
        suggestion.save(update_fields=["user_score"])

        return {"status": "success", "message": "Score updated successfully"}

    except Exception as e:
        logger.error("Failed to update title score", error=str(e), suggestion_id=suggestion_id, profile_id=profile.id)
        return {"status": "error", "message": f"Failed to update score: {str(e)}"}


@api.post("/add-pricing-page")
def add_pricing_page(request: HttpRequest, data: AddPricingPageIn):
    profile = request.auth
    project = Project.objects.get(id=data.project_id, profile=profile)

    project_page = ProjectPage.objects.create(project=project, url=data.url, type=ProjectPageType.PRICING)

    project_page.get_page_content()
    project_page.analyze_content()
    project_page.create_new_pricing_strategy()

    return {"status": "success", "message": "Pricing page added successfully"}


@api.post("/create-pricing-strategy")
def create_pricing_strategy(request: HttpRequest, data: CreatePricingStrategyIn):
    profile = request.auth
    project = Project.objects.get(id=data.project_id, profile=profile)

    project_page = ProjectPage.objects.filter(project=project, type=ProjectPageType.PRICING).latest("id")

    project_page.create_new_pricing_strategy(strategy_name=data.strategy_name, user_prompt=data.user_prompt)

    return {"status": "success", "message": "Pricing page added successfully"}


@api.post("/add-competitor", response=CompetitorAnalysisOut)
def add_competitor(request: HttpRequest, data: AddCompetitorIn):
    profile = request.auth
    project = get_object_or_404(Project, id=data.project_id, profile=profile)

    try:
        if Competitor.objects.filter(project=project, url=data.url).exists():
            return {"status": "error", "message": "This competitor already exists for your project"}

        competitor = Competitor.objects.create(
            project=project,
            name=data.name if hasattr(data, "name") and data.name else "Unknown Competitor",
            url=data.url,
            description=data.description if hasattr(data, "description") and data.description else "",
        )

        got_content = competitor.get_page_content()
        got_name_and_description = competitor.populate_name_description()

        if not got_content or not got_name_and_description:
            competitor.delete()
            return {"status": "error", "message": "Failed to get page content for this competitor URL"}

        analyzed = competitor.analyze_competitor()

        if not analyzed:
            competitor.delete()
            return {"status": "error", "message": "Failed to analyze this competitor"}

        return {
            "status": "success",
            "competitor_id": competitor.id,
            "name": competitor.name,
            "url": competitor.url,
            "description": competitor.description,
            "summary": competitor.summary,
            "competitor_analysis": competitor.competitor_analysis,
            "key_differences": competitor.key_differences,
            "strengths": competitor.strengths,
            "weaknesses": competitor.weaknesses,
            "opportunities": competitor.opportunities,
            "threats": competitor.threats,
            "key_features": competitor.key_features,
            "key_benefits": competitor.key_benefits,
            "key_drawbacks": competitor.key_drawbacks,
        }

    except Exception as e:
        logger.error("Failed to add competitor", error=str(e), exc_info=True, project_id=project.id, url=data.url)
        return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}


@api.post("/submit-feedback")
def submit_feedback(request: HttpRequest, data: SubmitFeedbackIn):
    profile = request.auth
    try:
        Feedback.objects.create(profile=profile, feedback=data.feedback, page=data.page)
        return {"status": "success", "message": "Feedback submitted successfully"}
    except Exception as e:
        logger.error("Failed to submit feedback", error=str(e), profile_id=profile.id)
        return {"status": "error", "message": "Failed to submit feedback. Please try again."}
