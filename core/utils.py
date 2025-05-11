import requests
from django.forms.utils import ErrorList

from core.models import AutoSubmittionSettings, GeneratedBlogPost, Project
from seo_blog_bot.utils import get_seo_blog_bot_logger

logger = get_seo_blog_bot_logger(__name__)


class DivErrorList(ErrorList):
    def __str__(self):
        return self.as_divs()

    def as_divs(self):
        if not self:
            return ""
        return f"""
            <div class="p-4 my-4 bg-red-50 rounded-md border border-red-600 border-solid">
              <div class="flex">
                <div class="flex-shrink-0">
                  <!-- Heroicon name: solid/x-circle -->
                  <svg class="w-5 h-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"> # noqa: E501
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" /> # noqa: E501
                  </svg>
                </div>
                <div class="ml-3 text-sm text-red-700">
                      {''.join([f'<p>{e}</p>' for e in self])}
                </div>
              </div>
            </div>
         """


def replace_placeholders(data, blog_post):
    """
    Recursively replace values in curly braces (e.g., '{slug}') in a dict with the corresponding attribute from blog_post.
    """
    if isinstance(data, dict):
        return {k: replace_placeholders(v, blog_post) for k, v in data.items()}
    elif isinstance(data, list):
        return [replace_placeholders(item, blog_post) for item in data]
    elif isinstance(data, str):
        import re

        def repl(match):
            attr = match.group(1).strip()
            # Support nested attributes (e.g., title.title)
            value = blog_post
            for part in attr.split("."):
                value = getattr(value, part, match.group(0))
                if value == match.group(0):
                    break
            return str(value)

        return re.sub(r"\{\{\s*(.*?)\s*\}\}", repl, data)
    else:
        return data


def submit_blog_post_to_endpoint(project_id, blog_post_id=None):
    """
    Submits the latest GeneratedBlogPost for the given project to the endpoint specified in AutoSubmittionSettings.
    Accepts a Project instance or project id.
    Returns the response object or error details.
    """
    if isinstance(project_id, int):
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            logger.error("Project not found", project_id=project_id)
            return {"error": "Project not found"}

    # Get latest GeneratedBlogPost
    if blog_post_id:
        blog_post = GeneratedBlogPost.objects.get(id=blog_post_id)
    else:
        blog_post = GeneratedBlogPost.objects.filter(project=project).order_by("-id").first()
    if not blog_post:
        logger.warning("No generated blog post found for project", project_id=project.id)
        return {"error": "No generated blog post found for project"}

    settings = AutoSubmittionSettings.objects.filter(project=project).order_by("-id").first()
    if not settings or not settings.endpoint_url:
        logger.warning("No AutoSubmittionSettings or endpoint_url found for project", project_id=project.id)
        return {"error": "No AutoSubmittionSettings or endpoint_url found for project"}

    url = settings.endpoint_url
    headers = replace_placeholders(settings.header, blog_post)
    body = replace_placeholders(settings.body, blog_post)

    try:
        logger.info("Submitting blog post to endpoint", url=url, project_id=project.id)
        response = requests.post(url, json=body, headers=headers, timeout=15)
        response.raise_for_status()
        logger.info("Successfully submitted blog post", status_code=response.status_code, project_id=project.id)
        return {"status": "success", "response": response.json()}
    except requests.RequestException as e:
        logger.error("Failed to submit blog post", error=str(e), url=url, project_id=project.id)
        return {"error": str(e), "status_code": getattr(e.response, "status_code", None)}
