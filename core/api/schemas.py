from ninja import Schema


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


class TitleSuggestionOut(Schema):
    category: str
    title: str
    description: str


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
