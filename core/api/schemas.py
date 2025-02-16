from ninja import Schema

from core.choices import ContentType


class ProjectScanIn(Schema):
    url: str


# TODO: what is the best practice on handling optional fields?
class ProjectScanOut(Schema):
    status: str
    message: str = ""
    project_id: int = 0
    name: str = ""
    type: str = ""
    url: str = ""
    summary: str = ""


class GenerateTitleSuggestionsIn(Schema):
    project_id: int
    content_type: str = ContentType.SHARING
    num_titles: int = 6


class TitleSuggestionOut(Schema):
    title: str
    category: str = ""  # For general titles
    description: str = ""  # For general titles
    search_intent: str = ""  # For SEO titles
    target_keywords: list[str] = []  # For SEO titles
    seo_score: int = 0  # For SEO titles
    reasoning: str = ""  # For SEO titles
    suggested_meta_description: str = ""  # For SEO titles


class GenerateTitleSuggestionsOut(Schema):
    suggestions: list[TitleSuggestionOut] = []
    status: str
    message: str = ""


class GeneratedContentOut(Schema):
    status: str
    message: str = ""
    content: str = ""
    slug: str = ""
    tags: str = ""
    description: str = ""


class GenerateTitleFromIdeaIn(Schema):
    project_id: int
    user_prompt: str


class GenerateTitleSuggestionOut(Schema):
    status: str
    message: str = ""
    suggestion: dict = {}
