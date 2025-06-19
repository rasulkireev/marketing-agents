import posthog
from django.forms.utils import ErrorList

from core.models import Profile, Project
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
    Recursively replace values in curly braces (e.g., '{{ slug }}') in a dict with the corresponding attribute from blog_post.
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


def get_or_create_project(profile_id, url, source=None):
    profile = Profile.objects.get(id=profile_id)
    project, created = Project.objects.get_or_create(profile=profile, url=url)

    project_metadata = {
        "project_id": project.id,
        "url": url,
        "source": source,
        "profile_id": profile_id,
        "profile_email": profile.user.email,
    }

    if created:
        posthog.capture(profile.user.email, "project_created", project_metadata)
        logger.info("[get_or_create_project] Project created", **project_metadata)
    else:
        logger.info("[get_or_create_project] Got existing project", **project_metadata)

    return project
