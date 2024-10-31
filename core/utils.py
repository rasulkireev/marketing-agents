import json
import anthropic

from django.forms.utils import ErrorList
from django.conf import settings
from django.db import transaction

from core.models import BlogPostTitleSuggestion, Profile, Project

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


def generate_blog_titles_with_claude(project_data: dict) -> list:
    """
    Generate blog titles using Claude
    """
    claude = anthropic.Client(api_key=settings.ANTHROPIC_API_KEY)

    prompt = f"""
    Generate blog post titles for the following project:
    - Project Name: {project_data['name']}
    - Project Type: {project_data['type']}
    - Project Summary: {project_data['summary']}
    - Blog Theme: {project_data['blog_theme']}
    - Key Features: {project_data['key_features']}
    - Target Audience: {project_data['target_audience_summary']}
    - Pain Points: {project_data['pain_points']}
    - Product Usage: {project_data['product_usage']}

    Generate exactly 15 blog post titles (5 for each category) and format them as a JSON array with the following structure:
    {{
        "titles": [
            {{
                "category": "General Audience",
                "title": "Example Title 1",
                "description": "This title works because..."
            }},
            {{
                "category": "Niche Audience",
                "title": "Example Title 2",
                "description": "This title works because..."
            }},
            {{
                "category": "Industry/Company",
                "title": "Example Title 3",
                "description": "This title works because..."
            }}
        ]
    }}

    Ensure each title:
    1. Is specific and clear about what the reader will learn
    2. Includes numbers where appropriate
    3. Creates curiosity without being clickbait
    4. Promises value or solution to a problem
    5. Is timeless rather than time-sensitive
    6. Uses power words to enhance appeal

    Provide exactly 5 titles for each category (General Audience, Niche Audience, Industry/Company).
    Return only valid JSON, no additional text or explanations outside the JSON structure.
    """

    try:
        message = claude.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=1500,
            temperature=0.7,
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        )
        response = message.content[0].text.strip()

        response = response.replace('\n', ' ').replace('\r', '')
        if response.startswith('```json'):
            response = response.replace('```json', '')
        if response.endswith('```'):
            response = response.replace('```', '')
        response = response.strip()

        data = json.loads(response)
        logger.info(
            "Got title suggestions from Clade",
            data=data
        )
        return data.get('titles', [])

    except json.JSONDecodeError as e:
        logger.error(
            "Error parsing JSON from Claude",
            error=str(e),
            prompt=prompt,
            response=response,
        )
        return []
    except Exception as e:
        logger.error(
            "Error generating titles with Claude",
            error=str(e),
            prompt=prompt,
        )
        return []


@transaction.atomic
def save_blog_titles(project_id: int, titles: list) -> None:
    """
    Save generated blog titles to the database
    """
    project = Project.objects.get(id=project_id)

    category_mapping = {
        'General Audience': BlogPostTitleSuggestion.Category.GENERAL_AUDIENCE,
        'Niche Audience': BlogPostTitleSuggestion.Category.NICH_AUDIENCE,
        'Industry/Company': BlogPostTitleSuggestion.Category.INDUSTRY_COMPANY
    }

    suggestions = []
    for title_data in titles:
        try:
            category = category_mapping.get(
                title_data['category'],
                BlogPostTitleSuggestion.Category.GENERAL_AUDIENCE
            )
            suggestions.append(
                BlogPostTitleSuggestion(
                    project=project,
                    title=title_data['title'],
                    description=title_data['description'],
                    category=category
                )
            )
        except KeyError as e:
            logger.error(
                "Missing required field in title data",
                error=str(e),
                title_data=title_data
            )
            continue

    if suggestions:
        BlogPostTitleSuggestion.objects.bulk_create(suggestions)
