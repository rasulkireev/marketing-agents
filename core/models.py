import json
from json.decoder import JSONDecodeError

import anthropic
import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models, transaction
from django.template.loader import render_to_string
from django.urls import reverse

from core.base_models import BaseModel
from core.choices import Category, ContentType
from core.model_utils import generate_random_key
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
    title = models.CharField(max_length=500, blank=True, default="")
    description = models.TextField(blank=True, default="")
    markdown_content = models.TextField(blank=True, default="")
    html_content = models.TextField(blank=True, default="")

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
            # First get the HTML content
            try:
                html_response = requests.get(self.url, timeout=30)
                html_response.raise_for_status()
                html_content = html_response.text
            except requests.exceptions.RequestException as e:
                logger.error("Error fetching HTML content", error=str(e), project_name=self.name, project_url=self.url)
                html_content = ""

            # Then get Jina Reader content
            jina_url = f"https://r.jina.ai/{self.url}"
            headers = {"Accept": "application/json", "Authorization": f"Bearer {settings.JINA_READER_API_KEY}"}

            response = requests.get(jina_url, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json().get("data", {})

            # Update the model fields
            self.title = data.get("title", "")[:500]  # Respect max_length
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

            logger.info("Successfully fetched content", project_name=self.name, project_url=self.url)

            return self.markdown_content

        except requests.exceptions.RequestException as e:
            logger.error(
                "Error fetching content from Jina Reader", error=str(e), project_name=self.name, project_url=self.url
            )
            raise ValueError(f"Error fetching content: {str(e)}")

    def analyze_content(self):
        """
        Analyze the page content using Claude and update project details.
        Should be called after get_page_content().
        """
        try:
            claude = anthropic.Client(api_key=settings.ANTHROPIC_API_KEY)

            prompt = render_to_string(
                "process_project_url.txt",
                {
                    "page_content": self.markdown_content,
                    "title": self.title,
                    "description": self.description,
                },
            )

            message = claude.messages.create(
                model="claude-3-5-sonnet-latest",
                max_tokens=1000,
                temperature=0,
                messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
            )
            response = message.content[0].text.strip()

            try:
                info = json.loads(response)
            except JSONDecodeError as e:
                logger.error(
                    "Error parsing JSON from Claude",
                    error=str(e),
                    prompt=prompt,
                    response=response,
                )
                raise ValueError("Failed to parse AI response")

            type_mapping = {choice[1]: choice[0] for choice in self.Type.choices}
            project_type = type_mapping.get(info.get("type", ""), self.Type.SAAS)

            self.name = info.get("name", "")
            self.type = project_type
            self.summary = info.get("summary", "")
            self.blog_theme = info.get("blog_theme", "")
            self.founders = info.get("founders", "")
            self.key_features = info.get("key_features", "")
            self.links = info.get("links", "")
            self.target_audience_summary = info.get("target_audience_summary", "")
            self.pain_points = info.get("pain_points", "")
            self.product_usage = info.get("product_usage", "")

            self.save(
                update_fields=[
                    "name",
                    "type",
                    "summary",
                    "blog_theme",
                    "founders",
                    "key_features",
                    "links",
                    "target_audience_summary",
                    "pain_points",
                    "product_usage",
                ]
            )

            logger.info("Successfully analyzed content", project_name=self.name, project_url=self.url)

        except Exception as e:
            logger.error("Error analyzing content", error=str(e), project_name=self.name, project_url=self.url)
            raise ValueError(f"Error analyzing content: {str(e)}")

    def generate_title_suggestions(self, content_type=ContentType.SHARING, num_titles=6):
        """
        Generates blog post title suggestions using Claude AI.
        Returns a tuple of (titles, status, message).
        """
        try:
            template_name = (
                "generate_blog_titles.txt"
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
            titles = data.get("titles", [])

            with transaction.atomic():
                suggestions = []

                if content_type == ContentType.SHARING:
                    for title_data in titles:
                        try:
                            suggestions.append(
                                BlogPostTitleSuggestion(
                                    project=self,
                                    title=title_data["title"],
                                    description=title_data["description"],
                                    category=title_data["category"],
                                    content_type=ContentType.SHARING,
                                    prompt=prompt,
                                )
                            )
                        except KeyError as e:
                            logger.error("Missing required field in title data", error=str(e), title_data=title_data)
                            continue
                else:  # SEO titles
                    for title_data in titles:
                        try:
                            suggestions.append(
                                BlogPostTitleSuggestion(
                                    project=self,
                                    title=title_data["title"],
                                    description=title_data["reasoning"],
                                    category=Category.GENERAL_AUDIENCE,
                                    content_type=ContentType.SEO,
                                    search_intent=title_data["search_intent"],
                                    target_keywords=title_data["target_keywords"],
                                    seo_score=title_data["seo_score"],
                                    suggested_meta_description=title_data["suggested_meta_description"],
                                    prompt=prompt,
                                )
                            )
                        except KeyError as e:
                            logger.error(
                                "Missing required field in SEO title data", error=str(e), title_data=title_data
                            )
                            continue

                if suggestions:
                    BlogPostTitleSuggestion.objects.bulk_create(suggestions)

            return titles, "success", "Successfully generated title suggestions"

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
    description = models.TextField()
    prompt = models.TextField(blank=True)
    category = models.CharField(max_length=50, choices=Category.choices, default=Category.GENERAL_AUDIENCE)
    content_type = models.CharField(max_length=20, choices=ContentType.choices, default=ContentType.SHARING)

    search_intent = models.CharField(max_length=50, blank=True)
    target_keywords = models.JSONField(default=list, blank=True, null=True)
    seo_score = models.IntegerField(default=0)
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
