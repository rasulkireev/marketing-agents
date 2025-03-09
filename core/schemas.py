from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from core.choices import ProjectPageType, ProjectType
from seo_blog_bot.utils import get_seo_blog_bot_logger

logger = get_seo_blog_bot_logger(__name__)


class WebPageContent(BaseModel):
    title: str
    description: str
    markdown_content: str
    html_content: str = Field(
        description="HTML content of the web page",
        default="",
    )


class ProjectDetails(BaseModel):
    name: str = Field(description="Official name of the project or organization")
    type: str = Field(
        description=(
            "Primary business model or project category."
            f"One of the following options: {', '.join([choice[0] for choice in ProjectType.choices])}"
        )
    )
    summary: str = Field(description="Comprehensive overview of the project's purpose and value proposition")
    blog_theme: str = Field(description="List of primary content themes and topics in markdown list format")
    founders: str = Field(description="List of founders with their roles in markdown list format")
    key_features: str = Field(description="List of main product capabilities in markdown list format")
    target_audience_summary: str = Field(description="Profile of ideal users including demographics and needs")
    pain_points: str = Field(description="List of target audience challenges in markdown list format")
    product_usage: str = Field(description="List of common use cases in markdown list format")
    links: str = Field(description="List of relevant URLs in markdown list format")
    language: str = Field(description="Language that the site uses.")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        valid_types = [choice[0] for choice in ProjectType.choices]

        if v not in valid_types:
            v_lower = v.lower()
            for valid_type in valid_types:
                if v_lower in valid_type.lower():
                    return valid_type

            logger.warning("[Project Details Schema] Type is not a valid option", provided_type=v)
            if len(v) > 50:
                return v
            else:
                return ProjectType.OTHER
        return v


class ProjectPageDetails(BaseModel):
    name: str = Field(description="Official name of the project or organization")
    type: str = Field(
        description=(
            "Primary business model or project category."
            f"One of the following options: {', '.join([choice[0] for choice in ProjectPageType.choices])}"
        )
    )
    type_ai_guess: str = Field(description="Page Type. Should never be 'Other'")
    summary: str = Field(description="Summary of the page content")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        valid_types = [choice[0] for choice in ProjectPageType.choices]

        if v not in valid_types:
            v_lower = v.lower()
            for valid_type in valid_types:
                if v_lower in valid_type.lower():
                    return valid_type

            logger.warning("[Project Details Schema] Type is not a valid option", provided_type=v)
            if len(v) > 50:
                return v
            else:
                return ProjectPageType.OTHER
        return v


class TitleSuggestionContext(BaseModel):
    """Context for generating blog post title suggestions."""

    project_details: ProjectDetails
    num_titles: int = Field(default=3, description="Number of title suggestions to generate")
    user_prompt: Optional[str] = Field(default=None, description="Optional user-provided guidance for title generation")
    liked_suggestions: Optional[List[str]] = Field(
        default_factory=list, description="Titles the user has previously liked"
    )
    disliked_suggestions: Optional[List[str]] = Field(
        default_factory=list, description="Titles the user has previously disliked"
    )


class TitleSuggestion(BaseModel):
    title: str = Field(description="SEO-optimized blog post title")
    category: str = Field(description="Primary content category")
    target_keywords: list[str] = Field(description="Strategic SEO keywords to target")
    description: str = Field(
        description="Brief overview of why this title is a good fit for the project and why it might work well for the target audience"
    )
    suggested_meta_description: str = Field(description="SEO-optimized meta description (150-160 characters)")


class TitleSuggestions(BaseModel):
    titles: list[TitleSuggestion] = Field(description="Collection of title suggestions with metadata")


class BlogPostGenerationContext(BaseModel):
    """Context for generating blog post content."""

    project_details: ProjectDetails
    title_suggestion: TitleSuggestion
    content_type: str = Field(description="Type of content to generate (SEO or SHARING)")


class BlogPostContent(BaseModel):
    description: str = Field(description="Meta description (150-160 characters) optimized for search engines")
    slug: str = Field(description="URL-friendly format using lowercase letters, numbers, and hyphens")
    tags: str = Field(description="5-8 relevant keywords as comma-separated values")
    content: str = Field(description="Full blog post content in Markdown format with proper structure and formatting")
