from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import NinjaAPI

from core.api.auth import MultipleAuthSchema
from core.api.schemas import (
    GeneratedContentOut,
    GenerateTitleSuggestionOut,
    GenerateTitleSuggestionsIn,
    GenerateTitleSuggestionsOut,
    ProjectScanIn,
    ProjectScanOut,
)
from core.choices import ContentType
from core.models import BlogPostTitleSuggestion, GeneratedBlogPost, Project
from seo_blog_bot.utils import get_seo_blog_bot_logger

logger = get_seo_blog_bot_logger(__name__)

api = NinjaAPI(auth=MultipleAuthSchema(), csrf=True)


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
        project.get_page_content()
        project.analyze_content()

        return {
            "status": "success",
            "project_id": project.id,
            "name": project.name,
            "type": project.get_type_display(),
            "url": project.url,
            "summary": project.summary,
        }

    except Exception as e:
        if project:
            project.delete()
        return {
            "status": "error",
            "message": str(e),
        }


@api.post("/generate-title-suggestions", response=GenerateTitleSuggestionsOut)
def generate_title_suggestions(request: HttpRequest, data: GenerateTitleSuggestionsIn):
    profile = request.auth
    logger.info(
        "[Generate Title Suggestions] API Called",
        project_id=data.project_id,
        profile_id=profile.id,
        content_type=data.content_type,
        number_of_titles=data.num_titles,
    )

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

    suggestions, status, message = project.generate_title_suggestions(
        content_type=content_type, num_titles=data.num_titles
    )

    return {"suggestions": suggestions, "status": status, "message": message or ""}


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
        # Convert string content_type to enum
        try:
            content_type = ContentType[data.content_type]
        except KeyError:
            return {"status": "error", "message": f"Invalid content type: {data.content_type}"}

        suggestion, status, message = project.generate_title_suggestions(
            content_type=content_type, num_titles=1, user_prompt=data.user_prompt  # Pass the converted content_type
        )

        if status == "success":
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
        else:
            return {"status": "error", "message": message}

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

    # Create a new blog post instance
    blog_post = GeneratedBlogPost.objects.create(
        project=suggestion.project,
        title=suggestion,
    )

    # Generate the content using the same content type as the suggestion
    status, message = blog_post.generate_content(content_type=suggestion.content_type)

    if status == "error":
        blog_post.delete()  # Clean up if generation failed
        return {
            "status": status,
            "message": message,
        }

    return {
        "status": status,
        "content": blog_post.content,
        "slug": blog_post.slug,
        "tags": blog_post.tags,
        "description": blog_post.description,
    }


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
