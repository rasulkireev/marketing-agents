import random
import string

import requests

from seo_blog_bot import settings
from seo_blog_bot.utils import get_seo_blog_bot_logger

logger = get_seo_blog_bot_logger(__name__)


def generate_random_key():
    characters = string.ascii_letters + string.digits
    return "".join(random.choice(characters) for _ in range(10))


def run_agent_synchronously(agent, input_string, deps=None):
    """
    Run a PydanticAI agent synchronously.

    Args:
        agent: The PydanticAI agent to run
        input_string: The input string to pass to the agent
        deps: Optional dependencies to pass to the agent

    Returns:
        The result of the agent run

    Raises:
        RuntimeError: If the agent execution fails
    """
    import asyncio

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        # Pass deps to the agent.run method if provided
        if deps is not None:
            result = loop.run_until_complete(agent.run(input_string, deps=deps))
        else:
            result = loop.run_until_complete(agent.run(input_string))
        return result
    except Exception as e:
        raise RuntimeError(f"Agent execution failed: {str(e)}") from e


def get_html_content(url):
    html_content = ""
    try:
        html_response = requests.get(url, timeout=30)
        html_response.raise_for_status()
        html_content = html_response.text
    except requests.exceptions.RequestException as e:
        logger.warning(
            "Could not fetch HTML content",
            error=str(e),
            url=url,
        )

    return html_content


def get_markdown_content(url):
    jina_url = f"https://r.jina.ai/{url}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {settings.JINA_READER_API_KEY}",
    }

    try:
        response = requests.get(jina_url, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json().get("data", {})

        return (
            data.get("title", "")[:500],
            data.get("description", ""),
            data.get("content", ""),
        )

    except requests.exceptions.RequestException as e:
        logger.error(
            "Error fetching content from Jina Reader",
            error=str(e),
            url=url,
        )
        return ("", "", "")
