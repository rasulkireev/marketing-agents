import json
import requests
import anthropic
from django.conf import settings

from core.models import Project
from seo_blog_bot.utils import get_seo_blog_bot_logger

logger = get_seo_blog_bot_logger(__name__)

def add_email_to_buttondown(email, tag):
    data = {
        "email_address": str(email),
        "metadata": {"source": tag},
        "tags": [tag],
        "referrer_url": "https://seo_blog_bot.app",
        "subscriber_type": "regular",
    }

    r = requests.post(
        "https://api.buttondown.email/v1/subscribers",
        headers={"Authorization": f"Token {settings.BUTTONDOWN_API_KEY}"},
        json=data,
    )

    return r.json()


def populate_project_fields(project_id: int):
    project = Project.objects.get(id=project_id)

    jina_url = f'https://r.jina.ai/{project.url}'
    jina_headers = {
        'Authorization': 'Bearer jina_79ed0444a37e40258d3b2f1f6bed6341YYruxpo_QlhqZNJUasu707xne3t6'
    }

    response = requests.get(jina_url, headers=jina_headers)
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
        info = json.loads(response)

        type_mapping = {choice[1]: choice[0] for choice in Project.Type.choices}
        project_type = type_mapping.get(info.get('type', ''), Project.Type.SAAS)

        project.name = info.get('name', '')
        project.type = project_type
        project.summary = info.get('summary', '')
        project.blog_theme = info.get('blog_theme', '')
        project.founders = info.get('founders', '')
        project.key_features = info.get('key_features', '')
        project.target_audience_summary = info.get('target_audience_summary', '')
        project.pain_points = info.get('pain_points', '')
        project.product_usage = info.get('product_usage', '')

        project.save()

    except json.JSONDecodeError as e:
        logger.error(
            "Error parsing JSON from Claude",
            error=str(e),
            prompt=prompt,
            response=response,
        )

    except Exception as e:
        logger.error(
            "Error updating project",
            error=str(e)
        )
