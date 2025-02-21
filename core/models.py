import json
import re

import anthropic
import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models, transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from pydantic_ai import Agent

from core.base_models import BaseModel
from core.choices import Category, ContentType
from core.model_utils import generate_random_key
from core.schemas import ProjectAnalysis
from seo_blog_bot.utils import get_seo_blog_bot_logger

logger = get_seo_blog_bot_logger(__name__)


class Profile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    key = models.CharField(max_length=10, unique=True, default=generate_random_key)

    subscription = models.ForeignKey(
        "djstripe.Subscription",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="profile",
        help_text="The user's Stripe Subscription object, if it exists",
    )
    customer = models.ForeignKey(
        "djstripe.Customer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="profile",
        help_text="The user's Stripe Customer object, if it exists",
    )

    def __str__(self):
        return f"{self.user.username}"

    def track_state_change(self, to_state, metadata=None):
        from_state = self.current_state

        if from_state != to_state:
            logger.info(
                "Tracking State Change", from_state=from_state, to_state=to_state, profile_id=self.id, metadata=metadata
            )
            ProfileStateTransition.objects.create(
                profile=self, from_state=from_state, to_state=to_state, backup_profile_id=self.id, metadata=metadata
            )

    @property
    def current_state(self):
        if not self.state_transitions.all().exists():
            return ProfileStates.STRANGER
        latest_transition = self.state_transitions.latest("created_at")
        return latest_transition.to_state

    @property
    def has_active_subscription(self):
        return self.current_state in [ProfileStates.SUBSCRIBED, ProfileStates.CANCELLED] or self.user.is_superuser

    @property
    def number_of_active_projects(self):
        return self.projects.count()

    @property
    def number_of_generated_blog_posts(self):
        projects = self.projects.all()
        return sum(project.generated_blog_posts.count() for project in projects)

    @property
    def number_of_title_suggestions(self):
        projects = self.projects.all()
        return sum(project.blog_post_title_suggestions.count() for project in projects)

    @property
    def reached_content_generation_limit(self):
        return self.number_of_generated_blog_posts >= 5 and not self.has_active_subscription

    @property
    def reached_title_generation_limit(self):
        return self.number_of_title_suggestions >= 20 and not self.has_active_subscription


class ProfileStates(models.TextChoices):
    STRANGER = "stranger"
    SIGNED_UP = "signed_up"
    SUBSCRIBED = "subscribed"
    CANCELLED = "cancelled"
    CHURNED = "churned"
    ACCOUNT_DELETED = "account_deleted"


class ProfileStateTransition(BaseModel):
    profile = models.ForeignKey(
        Profile, null=True, blank=True, on_delete=models.SET_NULL, related_name="state_transitions"
    )
    from_state = models.CharField(max_length=255, choices=ProfileStates.choices)
    to_state = models.CharField(max_length=255, choices=ProfileStates.choices)
    backup_profile_id = models.IntegerField()
    metadata = models.JSONField(null=True, blank=True)


class BlogPost(BaseModel):
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=250)
    tags = models.TextField()
    content = models.TextField()
    icon = models.ImageField(upload_to="blog_post_icons/", blank=True)
    image = models.ImageField(upload_to="blog_post_images/", blank=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("blog_post", kwargs={"slug": self.slug})


class Project(BaseModel):
    class Type(models.TextChoices):
        SAAS = "SaaS", "SaaS"
        HOSPITALITY = "Hospitality", "Hospitality"
        JOB_BOARD = "Job Board", "Job Board"
        LEGAL_SERVICES = "Legal Services", "Legal Services"
        MARKETING = "Marketing", "Marketing"
        NEWS_AND_MAGAZINE = "News and Magazine", "News and Magazine"
        ONLINE_TOOLS = "Online Tools, Utilities", "Online Tools, Utilities"
        ECOMMERCE = "Ecommerce", "Ecommerce"
        EDUCATIONAL = "Educational", "Educational"
        ENTERTAINMENT = "Entertainment", "Entertainment"
        FINANCIAL_SERVICES = "Financial Services", "Financial Services"
        HEALTH_AND_WELLNESS = "Health & Wellness", "Health & Wellness"
        PERSONAL_BLOG = "Personal Blog", "Personal Blog"
        REAL_ESTATE = "Real Estate", "Real Estate"
        SPORTS = "Sports", "Sports"
        TRAVEL_AND_TOURISM = "Travel and Tourism", "Travel and Tourism"

    class Style(models.TextChoices):
        DIGITAL_ART = "Digital Art", "Digital Art"
        PHOTOREALISTIC = "Photorealistic", "Photorealistic"
        HYPER_REALISTIC = "Hyper-realistic", "Hyper-realistic"
        OIL_PAINTING = "Oil Painting", "Oil Painting"
        WATERCOLOR = "Watercolor", "Watercolor"
        CARTOON = "Cartoon", "Cartoon"
        ANIME = "Anime", "Anime"
        THREE_D_RENDER = "3D Render", "3D Render"
        SKETCH = "Sketch", "Sketch"
        POP_ART = "Pop Art", "Pop Art"
        MINIMALIST = "Minimalist", "Minimalist"
        SURREALIST = "Surrealist", "Surrealist"
        IMPRESSIONIST = "Impressionist", "Impressionist"
        PIXEL_ART = "Pixel Art", "Pixel Art"
        CONCEPT_ART = "Concept Art", "Concept Art"
        ISOMETRIC = "Isometric", "Isometric"
        LOW_POLY = "Low Poly", "Low Poly"
        RETRO = "Retro", "Retro"
        CYBERPUNK = "Cyberpunk", "Cyberpunk"
        STEAMPUNK = "Steampunk", "Steampunk"

    class Language(models.TextChoices):
        ENGLISH = "English", "English"
        SPANISH = "Spanish", "Spanish"
        FRENCH = "French", "French"
        GERMAN = "German", "German"
        ITALIAN = "Italian", "Italian"
        PORTUGUESE = "Portuguese", "Portuguese"
        RUSSIAN = "Russian", "Russian"
        JAPANESE = "Japanese", "Japanese"
        CANTONESE = "Cantonese", "Cantonese"
        MANDARIN = "Mandarin", "Mandarin"
        ARABIC = "Arabic", "Arabic"
        KOREAN = "Korean", "Korean"
        HINDI = "Hindi", "Hindi"
        UKRAINIAN = "Ukrainian", "Ukrainian"
        # Add other languages as needed

    profile = models.ForeignKey(Profile, null=True, blank=True, on_delete=models.CASCADE, related_name="projects")
    url = models.URLField(max_length=200, unique=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50, choices=Type.choices, default=Type.SAAS)
    summary = models.TextField(blank=True)

    # Content from Jina Reader
    date_scraped = models.DateTimeField(null=True, blank=True)
    title = models.CharField(max_length=500, blank=True, default="")
    description = models.TextField(blank=True, default="")
    markdown_content = models.TextField(blank=True, default="")
    html_content = models.TextField(blank=True, default="")

    # AI Content
    date_analyzed = models.DateTimeField(null=True, blank=True)
    blog_theme = models.TextField(blank=True)
    founders = models.TextField(blank=True)
    key_features = models.TextField(blank=True)
    language = models.CharField(max_length=50, choices=Language.choices, default=Language.ENGLISH)
    target_audience_summary = models.TextField(blank=True)
    pain_points = models.TextField(blank=True)
    product_usage = models.TextField(blank=True)
    links = models.TextField(blank=True)
    style = models.CharField(max_length=50, choices=Style.choices, default=Style.DIGITAL_ART)

    def __str__(self):
        return self.name

    def get_page_content(self):
        """
        Fetch page content using Jina Reader API and update the project.
        Returns the content if successful, raises ValueError otherwise.
        """
        try:
            html_response = requests.get(self.url, timeout=30)
            html_response.raise_for_status()
            html_content = html_response.text
        except requests.exceptions.RequestException as e:
            logger.error(
                "[Get Page Content] Error fetching HTML content",
                error=str(e),
                project_name=self.name,
                project_url=self.url,
            )
            html_content = ""

        jina_url = f"https://r.jina.ai/{self.url}"
        headers = {"Accept": "application/json", "Authorization": f"Bearer {settings.JINA_READER_API_KEY}"}
        try:
            response = requests.get(jina_url, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json().get("data", {})

            self.date_scraped = timezone.now()
            self.title = data.get("title", "")[:500]
            self.description = data.get("description", "")
            self.markdown_content = data.get("content", "")
            self.html_content = html_content

            self.save(
                update_fields=[
                    "title",
                    "description",
                    "markdown_content",
                    "html_content",
                ]
            )

            logger.info(
                "[Page Content] Successfully fetched content",
                project_name=self.name,
                project_url=self.url,
            )

            return True

        except requests.exceptions.RequestException as e:
            logger.error(
                "[Page Content] Error fetching content from Jina Reader",
                error=str(e),
                project_name=self.name,
                project_url=self.url,
            )
            return False

    def analyze_content(self):
        """
        Analyze the page content using Claude via PydanticAI and update project details.
        Should be called after get_page_content().
        """
        agent = Agent(
            "google-gla:gemini-2.0-flash",
            result_type=ProjectAnalysis,
            system_prompt=(
                "You are an expert content analyzer. Based on the web page content provided, "
                "extract and infer the requested information. Make reasonable inferences based "
                "on available content, context, and industry knowledge."
            ),
        )

        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                agent.run(
                    f"""
                Web page content:
                Title: {self.title}
                Description: {self.description}
                Content: {self.markdown_content}
            """
                )
            )

            self.name = result.data.name
            self.type = result.data.type
            self.summary = result.data.summary
            self.blog_theme = result.data.blog_theme
            self.founders = result.data.founders
            self.key_features = result.data.key_features
            self.target_audience_summary = result.data.target_audience_summary
            self.pain_points = result.data.pain_points
            self.product_usage = result.data.product_usage
            self.links = result.data.links
            self.save()

            logger.info("[Analyze Content] Successfully analyzed content", project_name=self.name, project_url=self.url)

            return True

        except Exception as e:
            logger.error("[Analyze Content] Failed to analyze content", error=str(e), project_url=self.url)
            return False

    def generate_title_suggestions(self, content_type=ContentType.SHARING, num_titles=3, user_prompt=None):
        """
        Generates blog post title suggestions using Claude AI.
        If user_prompt is provided, generates a single title based on the prompt.
        Returns a tuple of (titles, status, message).
        """
        try:
            if user_prompt:
                template_name = (
                    "generate_blog_title_based_on_user_prompt_for_sharing.txt"
                    if content_type == ContentType.SHARING
                    else "generate_blog_title_based_on_user_prompt_for_seo.txt"
                )
                context = {"project": self, "user_prompt": user_prompt}
            else:
                template_name = (
                    "generate_blog_titles_for_sharing.txt"
                    if content_type == ContentType.SHARING
                    else "generate_blog_titles_for_seo.txt"
                )
                context = {"project": self, "num_titles": num_titles}

            prompt = render_to_string(template_name, context)

            claude = anthropic.Client(api_key=settings.ANTHROPIC_API_KEY)
            message = claude.messages.create(
                model="claude-3-5-sonnet-latest",
                max_tokens=1500,
                temperature=0.7,
                messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
            )
            response = message.content[0].text.strip()

            # Clean up the response
            response = response.replace("\n", " ").replace("\r", "")
            if response.startswith("```json"):
                response = response.replace("```json", "")
            if response.endswith("```"):
                response = response.replace("```", "")
            response = response.strip()

            data = json.loads(response)

            # Handle single title case
            if user_prompt:
                titles = [data]  # Wrap single title data in list for consistent processing
            else:
                titles = data.get("titles", [])

            with transaction.atomic():
                suggestions = []

                for title_data in titles:
                    try:
                        suggestion = BlogPostTitleSuggestion(
                            project=self,
                            title=title_data["title"],
                            description=title_data.get("description"),
                            category=title_data["category"],
                            content_type=content_type,
                            target_keywords=title_data.get("target_keywords", []),
                            suggested_meta_description=title_data.get("suggested_meta_description", ""),
                            prompt=user_prompt if user_prompt else prompt,
                        )
                        suggestions.append(suggestion)
                    except KeyError as e:
                        logger.error("Missing required field in title data", error=str(e), title_data=title_data)
                        continue

                if suggestions:
                    created_suggestions = BlogPostTitleSuggestion.objects.bulk_create(suggestions)

                    # Create a list of dictionaries with IDs included
                    suggestion_data = [
                        {
                            "id": suggestion.id,
                            "title": suggestion.title,
                            "description": suggestion.description,
                            "category": suggestion.category,
                            "target_keywords": suggestion.target_keywords,
                            "suggested_meta_description": suggestion.suggested_meta_description,
                        }
                        for suggestion in created_suggestions
                    ]

                    # For single title generation, return the first suggestion
                    if user_prompt:
                        return created_suggestions[0], "success", "Successfully generated title suggestion"

                    return suggestion_data, "success", "Successfully generated title suggestions"

            return [], "error", "No valid suggestions could be created"

        except json.JSONDecodeError as e:
            logger.error(
                "Error parsing JSON from Claude",
                error=str(e),
                prompt=prompt,
                response=response,
            )
            return [], "error", f"Error parsing response from AI: {str(e)}"


class BlogPostTitleSuggestion(BaseModel):
    project = models.ForeignKey(
        Project, null=True, blank=True, on_delete=models.CASCADE, related_name="blog_post_title_suggestions"
    )
    title = models.CharField(max_length=255)
    content_type = models.CharField(max_length=20, choices=ContentType.choices, default=ContentType.SHARING)
    category = models.CharField(max_length=50, choices=Category.choices, default=Category.GENERAL_AUDIENCE)
    description = models.TextField()
    prompt = models.TextField(blank=True)
    target_keywords = models.JSONField(default=list, blank=True, null=True)
    suggested_meta_description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.project.name}: {self.title}"


class GeneratedBlogPost(BaseModel):
    project = models.ForeignKey(
        Project, null=True, blank=True, on_delete=models.CASCADE, related_name="generated_blog_posts"
    )
    title = models.ForeignKey(
        BlogPostTitleSuggestion, null=True, blank=True, on_delete=models.CASCADE, related_name="generated_blog_posts"
    )
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=250)
    tags = models.TextField()
    content = models.TextField()
    icon = models.ImageField(upload_to="blog_post_icons/", blank=True)
    image = models.ImageField(upload_to="blog_post_images/", blank=True)

    def __str__(self):
        return f"{self.project.name}: {self.title.title}"

    def generate_content(self, content_type=ContentType.SHARING):
        """
        Generates blog post content using Claude AI.
        Returns a tuple of (status, message).
        """
        try:
            template_name = (
                "generate_blog_content_for_sharing.txt"
                if content_type == ContentType.SHARING
                else "generate_blog_content_for_seo.txt"
            )

            context = {"suggestion": self.title}
            prompt = render_to_string(template_name, context)

            claude = anthropic.Client(api_key=settings.ANTHROPIC_API_KEY)
            message = claude.messages.create(
                model="claude-3-5-sonnet-latest",
                max_tokens=8000,
                temperature=0.7,
                messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
            )

            # Clean and parse the response
            response_text = self._clean_response_text(message.content[0].text)
            response_json = self._parse_response_json(response_text)
            self._validate_response_json(response_json)

            # Update the blog post with generated content
            self.description = response_json["description"]
            self.slug = response_json["slug"]
            self.tags = response_json["tags"]
            self.content = response_json["content"]
            self.save()

            return "success", "Successfully generated blog post"

        except json.JSONDecodeError as e:
            logger.error(
                "Error parsing JSON from Claude",
                error=str(e),
                prompt=prompt,
                response=response_text,
            )
            return "error", f"Error parsing response from AI: {str(e)}"
        except Exception as e:
            logger.error(
                "Failed to generate blog content",
                error=str(e),
                title=self.title.title,
                project_id=self.project_id,
            )
            return "error", f"Failed to generate content: {str(e)}"

    def _clean_response_text(self, response_text):
        """Clean the response text from Claude."""
        response_text = response_text.strip()
        return "".join(char for char in response_text if ord(char) >= 32 or char in "\n\r\t")

    def _parse_response_json(self, response_text):
        """Parse the JSON response from Claude."""
        json_match = re.search(r"\{[\s\S]*\}", response_text)
        if json_match:
            response_text = json_match.group(0)

        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            response_text = response_text.replace("\n", "\\n").replace("\r", "\\r")
            return json.loads(response_text)

    def _validate_response_json(self, response_json):
        """Validate the required fields in the response JSON."""
        required_fields = ["description", "slug", "tags", "content"]
        missing_fields = [field for field in required_fields if field not in response_json]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        return response_json
