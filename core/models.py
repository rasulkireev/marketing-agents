import os
import time

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone
from pydantic_ai import Agent

from core.base_models import BaseModel
from core.choices import Category, ContentType
from core.model_utils import generate_random_key, run_agent_synchronously
from core.schemas import BlogPostContent, ProjectAnalysis, TitleSuggestions
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

    @property
    def project_details_string(self):
        return f"""
            - Today's Date: {timezone.now().strftime("%Y-%m-%d")}
            - Project URL: {self.url}
            - Project Name: {self.name}
            - Project Type: {self.type}
            - Project Summary: {self.summary}
            - Blog Theme: {self.blog_theme}
            - Founders: {self.founders}
            - Key Features: {self.key_features}
            - Target Audience: {self.target_audience_summary}
            - Pain Points: {self.pain_points}
            - Product Usage: {self.product_usage}
            - Language: {self.language}
            - Links: {self.links}
        """

    @property
    def liked_title_suggestions(self):
        return self.blog_post_title_suggestions.filter(user_score__gt=0).all()

    @property
    def disliked_title_suggestions(self):
        return self.blog_post_title_suggestions.filter(user_score__lt=0).all()

    @property
    def get_liked_disliked_title_suggestions_string(self):
        liked_titles = "\n".join(f"- {suggestion.title}" for suggestion in self.liked_title_suggestions)
        disliked_titles = "\n".join(f"- {suggestion.title}" for suggestion in self.disliked_title_suggestions)

        return f"""
            Liked Title Suggestions:
            {liked_titles}

            Disliked Title Suggestions:
            {disliked_titles}
        """

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

        result = run_agent_synchronously(
            agent,
            f"""
              Web page content:
              Title: {self.title}
              Description: {self.description}
              Content: {self.markdown_content}
            """,
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

    def generate_title_suggestions(self, content_type=ContentType.SHARING, num_titles=3, user_prompt=""):
        """Generate title suggestions based on content type."""
        if content_type == ContentType.SEO:
            return self.generate_seo_title_suggestions(num_titles, user_prompt)
        return self.generate_sharing_title_suggestions(num_titles, user_prompt)

    def create_blog_post_title_suggestions(self, titles, content_type: ContentType):
        with transaction.atomic():
            suggestions = []
            for title in titles:
                suggestion = BlogPostTitleSuggestion(
                    project=self,
                    title=title.title,
                    description=title.description,
                    category=title.category,
                    content_type=content_type,
                    target_keywords=title.target_keywords,
                    suggested_meta_description=title.suggested_meta_description,
                )
                suggestions.append(suggestion)

            return BlogPostTitleSuggestion.objects.bulk_create(suggestions)

    def generate_seo_title_suggestions(self, num_titles=3, user_prompt=None):
        agent = Agent(
            "google-gla:gemini-2.0-flash",
            result_type=TitleSuggestions,
            system_prompt="""
                You are an SEO expert. Based on the web page content provided,
                generate SEO-optimized blog post titles that are likely to perform well in search engines.
                Ensure each title:
                1. Contains primary keyword near the beginning
                2. Is between 50-60 characters long
                3. Uses proven CTR-boosting patterns (how-to, numbers, questions, etc.)
                4. Addresses specific search intent
                5. Includes power words that enhance click-through rates
                6. Maintains natural readability while being SEO-friendly
                7. Avoids keyword stuffing
                8. Uses modifiers like "best", "guide", "tips", where appropriate
            """,
        )

        result = run_agent_synchronously(
            agent,
            f"""
                {self.project_details_string}
                - Number of Titles: {num_titles}
                {f"- User's specific request: {user_prompt}" if user_prompt else ""}
                {self.get_liked_disliked_title_suggestions_string}
            """,
        )

        return self.create_blog_post_title_suggestions(result.data.titles, ContentType.SEO)

    def generate_sharing_title_suggestions(self, num_titles=3, user_prompt=None):
        agent = Agent(
            "google-gla:gemini-2.0-flash",
            result_type=TitleSuggestions,
            system_prompt="""
                You are Nicholas Cole, an expert in writing content that catches people's attention.
                Based on the web page content provided, generate blog post titles that are likely to
                perform well in search engines. Ensure each title:
                1. Is specific and clear about what the reader will learn
                2. Includes numbers where appropriate
                3. Creates curiosity without being clickbait
                4. Promises value or solution to a problem
                5. Is timeless rather than time-sensitive
                6. Uses power words to enhance appeal
            """,
        )

        result = run_agent_synchronously(
            agent,
            f"""
                {self.project_details_string}
                - Number of Titles: {num_titles}
                {f"- User's specific request: {user_prompt}" if user_prompt else ""}
                {self.get_liked_disliked_title_suggestions_string}
            """,
        )

        return self.create_blog_post_title_suggestions(result.data.titles, ContentType.SHARING)


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

    # User Interaction
    user_score = models.SmallIntegerField(
        default=0,
        choices=[
            (-1, "Didn't Like"),
            (0, "Undecided"),
            (1, "Liked"),
        ],
        help_text="User's rating of the title suggestion",
    )

    def __str__(self):
        return f"{self.project.name}: {self.title}"

    @property
    def title_suggestion_string(self):
        return f"""
            - Primary Keyword/Title: {self.title}
            - Category: {self.category}
            - Description: {self.description}
            - Target Keywords: {self.target_keywords}
            - Suggested Meta Description: {self.suggested_meta_description}
        """

    def get_agent(self, model="anthropic:claude-3-5-sonnet-latest", system_prompt="", retries=2):
        return Agent(
            model,
            retries=retries,
            result_type=BlogPostContent,
            system_prompt=system_prompt,
        )

    def save_article(self, result):
        return GeneratedBlogPost.objects.create(
            project=self.project,
            title=self,
            description=result.data.description,
            slug=result.data.slug,
            tags=result.data.tags,
            content=result.data.content,
        )

    def generate_seo_article(self):
        template_path = os.path.join(os.path.dirname(__file__), "prompts", "generate_blog_content_for_seo.txt")
        with open(template_path) as f:
            seo_description = f.read()

        model = "anthropic:claude-3-5-sonnet-latest"
        system_prompt = f"""You are an experienced SEO content strategist.
        You specialize in creating search-engine optimized content that ranks well
        and provide value to our target audience.
        Your task is to generate an SEO-optimized blog post. Given the title and description
        of the desired post. Here are some specific pointer:
        {seo_description}"""
        message = f"""
            {self.project.project_details_string}
            {self.title_suggestion_string}
        """
        max_retries = 2
        retry_count = 0
        last_error = None

        while retry_count < max_retries:
            try:
                logger.info(
                    "[Generate SEO Article] running agent",
                    system_prompt=system_prompt,
                    message=message,
                    suggestion_id=self.id,
                )
                result = run_agent_synchronously(
                    self.get_agent(model=model, system_prompt=system_prompt),
                    message,
                )
                logger.info(
                    "[Generate SEO Article] got AI result",
                    result=result,
                    data=result.data,
                    suggestion_id=self.id,
                )
                return self.save_article(result)
            except Exception as e:
                last_error = e
                if "overloaded_error" in str(e) and retry_count < max_retries - 1:
                    logger.warning(
                        "Overloaded error encountered, retrying",
                        error=str(e),
                        suggestion_id=self.id,
                        retry_count=retry_count + 1,
                    )
                    time.sleep(2)
                    retry_count += 1
                    continue
                elif "Exceeded maximum retries" in str(e):
                    logger.error(
                        "Exceeded maximum retries, swtiching model",
                        error=str(e),
                        suggestion_id=self.id,
                        retry_count=retry_count + 1,
                    )
                    time.sleep(2)
                    retry_count += 1
                    model = "google-gla:gemini-2.0-flash"
                    continue
                break

        if last_error:
            raise last_error

    def generate_sharing_article(self):
        template_path = os.path.join(os.path.dirname(__file__), "prompts", "generate_blog_content_for_seo.txt")
        with open(template_path) as f:
            sharing_description = f.read()

        model = "anthropic:claude-3-5-sonnet-latest"
        max_retries = 2
        retry_count = 0
        last_error = None
        system_prompt = f"""You are an experienced online writer.
              You understand both the art of capturing attention and
              the specific needs of our target audience.
              Your task is to generate a blog post.
              Here are some specific pointers:
              {sharing_description}"""
        message = f"""
            {self.project.project_details_string}
            {self.title_suggestion_string}
        """
        while retry_count < max_retries:
            try:
                logger.info(
                    "[Generate Sharing Article] running agent",
                    system_prompt=system_prompt,
                    message=message,
                    suggestion_id=self.id,
                )
                result = run_agent_synchronously(
                    self.get_agent(model=model, system_prompt=system_prompt),
                    message,
                )
                logger.info(
                    "[Generate Sharing Article] got AI result",
                    result=result,
                    data=result.data,
                    suggestion_id=self.id,
                )
                return self.save_article(result)
            except Exception as e:
                last_error = e
                if "overloaded_error" in str(e) and retry_count < max_retries - 1:
                    logger.warning(
                        "Overloaded error encountered, retrying",
                        error=str(e),
                        suggestion_id=self.id,
                        retry_count=retry_count + 1,
                    )
                    time.sleep(2)
                    retry_count += 1
                    continue
                elif "Exceeded maximum retries" in str(e):
                    logger.error(
                        "Exceeded maximum retries, swtiching model",
                        error=str(e),
                        suggestion_id=self.id,
                        retry_count=retry_count + 1,
                    )
                    time.sleep(2)
                    retry_count += 1
                    model = "google-gla:gemini-2.0-flash"
                    continue
                break

        if last_error:
            raise last_error

    def generate_content(self, content_type=ContentType.SHARING):
        if content_type == ContentType.SEO:
            return self.generate_seo_article()
        return self.generate_sharing_article()


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
