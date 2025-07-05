from pydantic_ai import Agent, RunContext

from core.schemas import ProjectDetails, WebPageContent

analyze_project_agent = Agent(
    "google-gla:gemini-2.5-flash",
    output_type=ProjectDetails,
    deps_type=WebPageContent,
    system_prompt=(
        "You are an expert content analyzer. Based on the content provided, "
        "extract and infer the requested information. Make reasonable inferences based "
        "on available content, context, and industry knowledge."
    ),
    retries=2,
)


@analyze_project_agent.system_prompt
def add_webpage_content(ctx: RunContext[WebPageContent]) -> str:
    return (
        "Web page content:"
        f"Title: {ctx.deps.title}"
        f"Description: {ctx.deps.description}"
        f"Content: {ctx.deps.markdown_content}"
        f"HTML Content: {ctx.deps.html_content}"
    )
