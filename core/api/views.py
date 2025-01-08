import json
import re
from json.decoder import JSONDecodeError

import anthropic
import requests
from django.conf import settings
from django.db import transaction
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from ninja import NinjaAPI

from core.api.auth import MultipleAuthSchema
from core.api.schemas import (
    GeneratedContentOut,
    GenerateTitleFromIdeaIn,
    GenerateTitleSuggestionOut,
    GenerateTitleSuggestionsIn,
    GenerateTitleSuggestionsOut,
    ProjectScanIn,
    ProjectScanOut,
)
from core.models import BlogPostTitleSuggestion, GeneratedBlogPost, Project
from seo_blog_bot.utils import get_seo_blog_bot_logger

logger = get_seo_blog_bot_logger(__name__)

api = NinjaAPI(auth=MultipleAuthSchema(), csrf=True)


@api.post("/scan", response=ProjectScanOut)
def scan_project(request: HttpRequest, data: ProjectScanIn):
    logger.info("[Scan Project] API Called")

    profile = request.auth

    # Check if project already exists for this user
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

    project = Project.objects.create(profile=profile, url=data.url)
    try:
        # Get page content from Jina
        jina_url = f"https://r.jina.ai/{data.url}"
        jina_headers = {"Authorization": f"Bearer {settings.JINA_READER_API_KEY}"}

        try:
            response = requests.get(jina_url, headers=jina_headers)
        except ConnectionError as e:
            logger.error("Failed to get info from Jina Reader AI.", error=str(e))
            raise ValueError("Failed to get info from Jina Reader AI")

        page_content = response.text

        # Process with Claude
        claude = anthropic.Client(api_key=settings.ANTHROPIC_API_KEY)

        # Render the prompt template with context
        prompt = render_to_string("process_project_url.txt", {"page_content": page_content})

        message = claude.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=1000,
            temperature=0,
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        )
        response = message.content[0].text.strip()

        try:
            info = json.loads(response)
        except JSONDecodeError as e:
            logger.error(
                "Error parsing JSON from Claude",
                error=str(e),
                prompt=prompt,
                response=response,
            )
            raise ValueError("Failed to parse AI response")

        # Map project type
        type_mapping = {choice[1]: choice[0] for choice in Project.Type.choices}
        project_type = type_mapping.get(info.get("type", ""), Project.Type.SAAS)

        project.name = info.get("name", "")
        project.type = project_type
        project.summary = info.get("summary", "")
        project.blog_theme = info.get("blog_theme", "")
        project.founders = info.get("founders", "")
        project.key_features = info.get("key_features", "")
        project.links = info.get("links", "")
        project.target_audience_summary = info.get("target_audience_summary", "")
        project.pain_points = info.get("pain_points", "")
        project.product_usage = info.get("product_usage", "")
        project.save()

    except Exception as e:
        logger.error("Error processing project", error=str(e), project_id=project.id)
        project.delete()
        raise ValueError(f"Error processing URL: {str(e)}")

    return {
        "status": "success",
        "project_id": project.id,
        "name": project.name,
        "type": project.get_type_display(),
        "url": project.url,
        "summary": project.summary,
    }


@api.post("/generate-title-suggestions", response=GenerateTitleSuggestionsOut)
def generate_title_suggestions(request: HttpRequest, data: GenerateTitleSuggestionsIn):
    profile = request.auth

    logger.info("[Generate Title Suggestions] API Called", project_id=data.project_id, profile_id=profile.id)

    project = get_object_or_404(Project, id=data.project_id, profile=profile)

    if (
        # don't want to generate 15 new suggestions if user has a bunch already.
        profile.number_of_title_suggestions + 15 >= 20
        and not profile.has_active_subscription
    ):
        return {
            "suggestions": [],
            "status": "error",
            "message": "Title generation limit reached. Consider <a class='underline' href='/pricing'>upgrading</a>?",
        }

    try:
        prompt = render_to_string("generate_blog_titles.txt", {"project": project})

        claude = anthropic.Client(api_key=settings.ANTHROPIC_API_KEY)
        message = claude.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=1500,
            temperature=0.7,
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        )
        response = message.content[0].text.strip()

        response = response.replace("\n", " ").replace("\r", "")
        if response.startswith("```json"):
            response = response.replace("```json", "")
        if response.endswith("```"):
            response = response.replace("```", "")
        response = response.strip()

        data = json.loads(response)
        titles = data.get("titles", [])

        with transaction.atomic():
            category_mapping = {
                "General Audience": BlogPostTitleSuggestion.Category.GENERAL_AUDIENCE,
                "Niche Audience": BlogPostTitleSuggestion.Category.NICH_AUDIENCE,
                "Industry/Company": BlogPostTitleSuggestion.Category.INDUSTRY_COMPANY,
            }

            suggestions = []
            for title_data in titles:
                try:
                    category = category_mapping.get(
                        title_data["category"], BlogPostTitleSuggestion.Category.GENERAL_AUDIENCE
                    )
                    suggestions.append(
                        BlogPostTitleSuggestion(
                            project=project,
                            title=title_data["title"],
                            description=title_data["description"],
                            category=category,
                        )
                    )
                except KeyError as e:
                    logger.error("Missing required field in title data", error=str(e), title_data=title_data)
                    continue

            if suggestions:
                BlogPostTitleSuggestion.objects.bulk_create(suggestions)

        return {
            "suggestions": titles,
            "status": "success",
        }

    except json.JSONDecodeError as e:
        logger.error(
            "Error parsing JSON from Claude",
            error=str(e),
            prompt=prompt,
            response=response,
        )
        raise ValueError(f"Error parsing response from AI: {str(e)}")

    except Exception as e:
        logger.error("Error generating title suggestions", error=str(e), project_id=project.id)
        raise ValueError(f"Error generating title suggestions: {str(e)}")


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
        claude = anthropic.Client(api_key=settings.ANTHROPIC_API_KEY)
        prompt = render_to_string("generate_blog_content.txt", {"suggestion": suggestion})
        message = claude.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=8000,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}],
        )

        # Clean and parse the response
        response_text = message.content[0].text.strip()
        response_text = "".join(char for char in response_text if ord(char) >= 32 or char in "\n\r\t")

        # Extract JSON content
        json_match = re.search(r"\{[\s\S]*\}", response_text)
        if json_match:
            response_text = json_match.group(0)

        # Parse the cleaned JSON
        try:
            response_json = json.loads(response_text)
        except json.JSONDecodeError:
            response_text = response_text.replace("\n", "\\n").replace("\r", "\\r")
            response_json = json.loads(response_text)

        required_fields = ["description", "slug", "tags", "content"]
        missing_fields = [field for field in required_fields if field not in response_json]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        generated_post = GeneratedBlogPost.objects.create(
            project=suggestion.project,
            title=suggestion,
            slug=response_json["slug"],
            description=response_json["description"],
            tags=response_json["tags"],
            content=response_json["content"],
        )

        return {
            "status": "success",
            "content": generated_post.content,
            "slug": generated_post.slug,
            "tags": generated_post.tags,
            "description": generated_post.description,
        }

    except Exception as e:
        logger.error(
            "Failed to generate blog content",
            error=str(e),
            title=suggestion.title,
            project_id=suggestion.project.id,
        )
        raise ValueError(f"Failed to generate content: {str(e)}")


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


@api.post("/generate-title-from-idea", response=GenerateTitleSuggestionOut)
def generate_title_from_idea(request: HttpRequest, data: GenerateTitleFromIdeaIn):
    profile = request.auth
    project = get_object_or_404(Project, id=data.project_id, profile=profile)

    if profile.reached_title_generation_limit:
        return {
            "status": "error",
            "message": "Title generation limit reached. Consider <a class='underline' href='/pricing'>upgrading</a>?",
        }

    try:
        prompt = render_to_string(
            "generate_blog_title_based_on_user_prompt.txt", {"project": project, "user_prompt": data.user_prompt}
        )

        claude = anthropic.Client(api_key=settings.ANTHROPIC_API_KEY)
        message = claude.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=1500,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}],
        )
        response = message.content[0].text.strip()

        # Clean and parse the response
        if response.startswith("```json"):
            response = response.replace("```json", "")
        if response.endswith("```"):
            response = response.replace("```", "")
        response = response.strip()

        claude_data = json.loads(response)

        # Create the suggestion in the database
        suggestion = BlogPostTitleSuggestion.objects.create(
            project=project,
            title=claude_data["title"],
            description=claude_data["description"],
            category=claude_data["category"],
            prompt=data.user_prompt,
        )

        return {
            "status": "success",
            "suggestion": {
                "id": suggestion.id,
                "title": suggestion.title,
                "description": suggestion.description,
                "category": suggestion.get_category_display(),
            },
        }

    except Exception as e:
        logger.error(
            "Failed to generate title from idea", error=str(e), project_id=project.id, user_prompt=data.user_prompt
        )
        raise ValueError(f"Failed to generate title: {str(e)}")
