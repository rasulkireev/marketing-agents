import json

import anthropic
import requests
from django.conf import settings
from django.forms.utils import ErrorList
from requests.exceptions import ConnectionError

from core.models import Profile
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


def check_if_profile_has_pro_subscription(profile_id):
    has_pro_subscription = False
    if profile_id:
        try:
            profile = Profile.objects.get(id=profile_id)
            has_pro_subscription = profile.subscription is not None
        except Profile.DoesNotExist:
            logger.error("Profile does not exist", profile_id=profile_id)

    return has_pro_subscription


def process_project_url(url: str) -> dict:
    jina_url = f"https://r.jina.ai/{url}"
    jina_headers = {"Authorization": f"Bearer {settings.JINA_READER_API_KEY}"}

    try:
        response = requests.get(jina_url, headers=jina_headers)
    except ConnectionError as e:
        logger.error("Failed to get info from Jina Reader AI.", error=str(e))
        raise ValueError("Failed to get info from Jina Reader AI")

    page_content = response.text

    claude = anthropic.Client(api_key=settings.ANTHROPIC_API_KEY)

    prompt = f"""
    Based on the following web page content, please extract information to populate a Project object. If any information is not available, leave it as an empty string.

    Web page content:
    {page_content}

    Please provide the information in a JSON format with the following structure:
    {{
        "name": "Project name",
        "type": "One of: SaaS, Hospitality, Job Board, Legal Services, Marketing, News and Magazine, Online Tools, Ecommerce, Educational, Entertainment, Financial Services, Health & Wellness, Personal Blog, Real Estate, Sports, Travel and Tourism",
        "summary": "Brief summary of the website/project",
        "blog_theme": "Main topics or theme of the blog/content",
        "founders": "Names of founders if mentioned",
        "key_features": "Key features or functionalities",
        "target_audience_summary": "Description of target audience",
        "pain_points": "Problems or challenges addressed",
        "product_usage": "How the product/service is typically used"
    }}

    Return only the JSON object, nothing else. Ensure it's valid JSON format.
    """

    message = claude.messages.create(
        model="claude-3-5-sonnet-latest",
        max_tokens=1000,
        temperature=0,
        messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
    )
    response = message.content[0].text.strip()

    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        logger.error(
            "Error parsing JSON from Claude",
            error=str(e),
            prompt=prompt,
            response=response,
        )
        raise ValueError("Failed to parse AI response")
