import json
import re

import anthropic
from django.conf import settings
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from ninja import NinjaAPI

from core.api.auth import MultipleAuthSchema
from core.api.schemas import (
    GeneratedContentOut,
    GenerateTitleSuggestionsIn,
    GenerateTitleSuggestionsOut,
    ProjectScanIn,
    ProjectScanOut,
)
from core.models import BlogPostTitleSuggestion, GeneratedBlogPost, Project
from core.utils import generate_blog_titles_with_claude, process_project_url, save_blog_titles
from seo_blog_bot.utils import get_seo_blog_bot_logger

logger = get_seo_blog_bot_logger(__name__)

api = NinjaAPI(auth=MultipleAuthSchema(), csrf=True)  # Enable CSRF protection


@api.post("/scan", response=ProjectScanOut)
def scan_project(request: HttpRequest, data: ProjectScanIn):
    profile = request.auth

    # Check if project already exists for this user
    project = Project.objects.filter(profile=profile, url=data.url).first()

    if project:
        return {
            "project_id": project.id,
            "has_details": bool(project.name),
            "has_suggestions": project.blog_post_title_suggestions.exists(),
        }

    # Create new project
    project = Project.objects.create(profile=profile, url=data.url)

    try:
        # Process the URL synchronously
        info = process_project_url(data.url)

        type_mapping = {choice[1]: choice[0] for choice in Project.Type.choices}
        project_type = type_mapping.get(info.get("type", ""), Project.Type.SAAS)

        # Update project with processed information
        project.name = info.get("name", "")
        project.type = project_type
        project.summary = info.get("summary", "")
        project.blog_theme = info.get("blog_theme", "")
        project.founders = info.get("founders", "")
        project.key_features = info.get("key_features", "")
        project.target_audience_summary = info.get("target_audience_summary", "")
        project.pain_points = info.get("pain_points", "")
        project.product_usage = info.get("product_usage", "")
        project.save()

    except Exception as e:
        logger.error("Error processing project", error=str(e), project_id=project.id)
        project.delete()
        raise ValueError(f"Error processing URL: {str(e)}")

    return {
        "project_id": project.id,
        "name": project.name,
        "type": project.get_type_display(),
        "url": project.url,
        "summary": project.summary,
    }


@api.post("/generate-title-suggestions", response=GenerateTitleSuggestionsOut)
def generate_title_suggestions(request: HttpRequest, data: GenerateTitleSuggestionsIn):
    profile = request.auth

    # Get project and verify ownership
    project = get_object_or_404(Project, id=data.project_id, profile=profile)

    # Prepare project data
    project_data = {
        "name": project.name,
        "type": project.type,
        "summary": project.summary,
        "blog_theme": project.blog_theme,
        "key_features": project.key_features,
        "target_audience_summary": project.target_audience_summary,
        "pain_points": project.pain_points,
        "product_usage": project.product_usage,
    }

    try:
        titles = generate_blog_titles_with_claude(project_data)
        save_blog_titles(project.id, titles)

        return {"suggestions": titles}

    except Exception as e:
        logger.error("Error generating title suggestions", error=str(e), project_id=project.id)
        raise ValueError(f"Error generating title suggestions: {str(e)}")


@api.post("/generate-blog-content/{suggestion_id}", response=GeneratedContentOut)
def generate_blog_content(request: HttpRequest, suggestion_id: int):
    suggestion = get_object_or_404(BlogPostTitleSuggestion, id=suggestion_id, project__profile=request.auth)

    # Create a placeholder GeneratedBlogPost
    generated_post = GeneratedBlogPost.objects.create(
        project=suggestion.project,
        title=suggestion,
        slug=slugify(suggestion.title),
        description=suggestion.description,
        tags="",
        content="",
    )

    try:
        claude = anthropic.Client(api_key=settings.ANTHROPIC_API_KEY)

        prompt = f"""You are an experienced online writer for {suggestion.project.name}, a {suggestion.project.type} platform. You understand both the art of capturing attention and the specific needs of our target audience: {suggestion.project.target_audience_summary}

Your task is to generate a blog post and return it in the following JSON format. Ensure the JSON is properly escaped and contains no control characters or line breaks within field values:

{{
    "description": "A single-line meta description (150-160 characters)",
    "slug": "url-friendly-version-of-title",
    "tags": "Tag 1, Tag 2, Tag 3, Tag 4, Tag 5",
    "content": "The full blog post content in Markdown"
}}

Context for content generation:
- Platform: {suggestion.project.name} ({suggestion.project.type})
- Key features: {suggestion.project.key_features}
- Pain points addressed: {suggestion.project.pain_points}
- Target audience: {suggestion.project.target_audience_summary}
- Usage patterns: {suggestion.project.product_usage}
- Blog theme: {suggestion.project.blog_theme}

For the given title '{suggestion.title}', please create:

1. Description:
- Write a compelling 150-160 character meta description
- Focus on value proposition and SEO
- Single line, no line breaks

2. Slug:
- Convert title to URL-friendly format
- Use lowercase letters, numbers, and hyphens only
- Remove special characters and spaces

3. Tags:
- Generate 5-8 relevant keywords
- Comma-separated, no spaces
- Relevant to {suggestion.project.type} industry
- Include general and specific terms

4. Content:
- Full blog post in Markdown format
- Follow the structure:
  * Strong opening hook
  * 3-5 main points with examples
  * Clear conclusion with call-to-action
- Maintain professional tone for {suggestion.project.type} sector
- Address target audience pain points
- Reference key features where relevant
- Optimize for online readability

IMPORTANT: Ensure the response is a valid JSON object. All string values must be properly escaped. Do not include line breaks within JSON field values except in the "content" field where Markdown formatting is used."""

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

        # Update the generated post
        generated_post.description = response_json["description"]
        generated_post.slug = response_json["slug"]
        generated_post.tags = response_json["tags"]
        generated_post.content = response_json["content"]
        generated_post.save()

        return {
            "status": "success",
            "content": response_json["content"],
            "slug": response_json["slug"],
            "tags": response_json["tags"],
            "description": response_json["description"],
        }

    except Exception as e:
        logger.error(
            "Failed to generate blog content",
            error=str(e),
            post_id=generated_post.id,
            title=suggestion.title,
            project_id=suggestion.project.id,
        )
        generated_post.delete()
        raise ValueError(f"Failed to generate content: {str(e)}")
