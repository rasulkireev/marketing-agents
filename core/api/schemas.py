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


class AddCompetitorIn(Schema):
    project_id: int
    url: str
    name: Optional[str] = None
    description: Optional[str] = None


class CompetitorAnalysisOut(Schema):
    status: str
    message: Optional[str] = None
    competitor_id: Optional[int] = None
    name: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    summary: Optional[str] = None
    competitor_analysis: Optional[str] = None
    key_differences: Optional[str] = None
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    opportunities: Optional[str] = None
    threats: Optional[str] = None
    key_features: Optional[str] = None
    key_benefits: Optional[str] = None
    key_drawbacks: Optional[str] = None
