from pydantic import BaseModel, Field


class ProjectAnalysis(BaseModel):
    name: str = Field(description="Official project/company name")
    type: str = Field(description="Project type (e.g., SaaS, Ecommerce)")
    summary: str = Field(description="4-5 sentence description of what the project does")
    blog_theme: str = Field(description="Content themes and topics, separated by semicolons")
    founders: str = Field(description="Names and roles of founders, separated by semicolons")
    key_features: str = Field(description="List of features and functionalities, separated by semicolons")
    target_audience_summary: str = Field(description="Detailed profile of target users")
    pain_points: str = Field(description="Problems and challenges addressed, separated by semicolons")
    product_usage: str = Field(description="How users interact with the product, separated by semicolons")
    links: str = Field(description="List of links found on the page")


class TitleSuggestion(BaseModel):
    title: str = Field(description="Blog post title")
    category: str = Field(description="Category of the blog post")
    target_keywords: list[str] = Field(description="Target keywords for the blog post")
    description: str = Field(description="Description of the blog post")
    suggested_meta_description: str = Field(description="Suggested meta description for the blog post")


class TitleSuggestions(BaseModel):
    titles: list[TitleSuggestion] = Field(description="List of title suggestions")
