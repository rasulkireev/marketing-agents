from pydantic import BaseModel, Field


class WebPageContent(BaseModel):
    title: str
    description: str
    html_content: str
    markdown_content: str


class ProjectAnalysis(BaseModel):
    name: str = Field(description="Official name of the project or organization")
    type: str = Field(description="Primary business model or project category")
    summary: str = Field(description="Comprehensive overview of the project's purpose and value proposition")
    blog_theme: str = Field(description="List of primary content themes and topics in markdown list format")
    founders: str = Field(description="List of founders with their roles in markdown list format")
    key_features: str = Field(description="List of main product capabilities in markdown list format")
    target_audience_summary: str = Field(description="Profile of ideal users including demographics and needs")
    pain_points: str = Field(description="List of target audience challenges in markdown list format")
    product_usage: str = Field(description="List of common use cases in markdown list format")
    links: str = Field(description="List of relevant URLs in markdown list format")


class TitleSuggestion(BaseModel):
    title: str = Field(description="SEO-optimized blog post title")
    category: str = Field(description="Primary content category")
    target_keywords: list[str] = Field(description="Strategic SEO keywords to target")
    description: str = Field(description="Brief overview of the blog post's main points as comma-separated keywords")
    suggested_meta_description: str = Field(description="SEO-optimized meta description (150-160 characters)")


class TitleSuggestions(BaseModel):
    titles: list[TitleSuggestion] = Field(description="Collection of title suggestions with metadata")


class BlogPostContent(BaseModel):
    description: str = Field(description="Meta description (150-160 characters) optimized for search engines")
    slug: str = Field(description="URL-friendly format using lowercase letters, numbers, and hyphens")
    tags: str = Field(description="5-8 relevant keywords as comma-separated values")
    content: str = Field(description="Full blog post content in Markdown format with proper structure and formatting")
