from typing import Optional

from ninja import Schema

from core.choices import ContentType


class ProjectScanIn(Schema):
    url: str


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
    user_prompt: str = ""
    num_titles: int = 3


class TitleSuggestionOut(Schema):
    id: int
    title: str
    category: str = ""
    description: str = ""
    target_keywords: list[str] = []
    suggested_meta_description: str = ""


class GenerateTitleSuggestionOut(Schema):
    status: str
    message: str = ""
    suggestion: TitleSuggestionOut = {}


class GenerateTitleSuggestionsOut(Schema):
    suggestions: list[TitleSuggestionOut] = []
    status: str
    message: str = ""


class GeneratedContentOut(Schema):
    status: str = "success"
    message: Optional[str] = None
    content: Optional[str] = None
    slug: Optional[str] = None
    tags: Optional[str] = None
    description: Optional[str] = None


class UpdateTitleScoreIn(Schema):
    score: int


class AddPricingPageIn(Schema):
    project_id: int
    url: str


class CreatePricingStrategyIn(Schema):
    project_id: int
    strategy_name: str = "Alex Hormozi"
    user_prompt: str = ""
