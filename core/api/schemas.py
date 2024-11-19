from ninja import Schema


class ProjectScanIn(Schema):
    url: str


class ProjectScanOut(Schema):
    project_id: int
    name: str = ""
    type: str = ""
    url: str
    summary: str = ""


class GenerateTitleSuggestionsIn(Schema):
    project_id: int


class TitleSuggestionOut(Schema):
    category: str
    title: str
    description: str


class GenerateTitleSuggestionsOut(Schema):
    suggestions: list[TitleSuggestionOut]


class GeneratedContentOut(Schema):
    status: str
    content: str
    slug: str
    tags: str
    description: str
