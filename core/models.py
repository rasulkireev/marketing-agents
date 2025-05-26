from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone
from django_q.tasks import async_task
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from core.base_models import BaseModel
from core.choices import (
    BlogPostStatus,
    Category,
    ContentType,
    KeywordDataSource,
    Language,
    ProfileStates,
    ProjectPageType,
    ProjectStyle,
    ProjectType,
)
from core.model_utils import generate_random_key, get_html_content, get_markdown_content, run_agent_synchronously
from core.prompts import (
    GENERATE_CONTENT_SYSTEM_PROMPTS,
    PRICING_PAGE_STRATEGY_SYSTEM_PROMPT,
    TITLE_SUGGESTION_SYSTEM_PROMPTS,
)
from core.schemas import (
    BlogPostContent,
    BlogPostGenerationContext,
    CompetitorAnalysis,
    CompetitorAnalysisContext,
    CompetitorDetails,
    PricingPageStrategyContext,
    PricingPageStrategySuggestion,
    ProjectDetails,
    ProjectPageContext,
    ProjectPageDetails,
    TitleSuggestion,
    TitleSuggestionContext,
    TitleSuggestions,
    WebPageContent,
)
from core.utils import replace_placeholders
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
    product = models.ForeignKey(
        "djstripe.Product",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="profile",
        help_text="The user's Stripe Product object, if it exists",
    )
    customer = models.ForeignKey(
        "djstripe.Customer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="profile",
        help_text="The user's Stripe Customer object, if it exists",
    )

    state = models.CharField(
        max_length=255,
        choices=ProfileStates.choices,
        default=ProfileStates.STRANGER,
        help_text="The current state of the user's profile",
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
            self.state = to_state
            self.save(update_fields=["state"])

    @property
    def current_state(self):
        if not self.state_transitions.all().exists():
            return ProfileStates.STRANGER
        latest_transition = self.state_transitions.latest("created_at")
        return latest_transition.to_state

    @property
    def has_active_subscription(self):
        return (
            self.current_state
            in [
                ProfileStates.SUBSCRIBED,
                ProfileStates.CANCELLED,
            ]
            or self.user.is_superuser
        )

    @property
    def has_product_or_subscription(self):
        return self.product is not None or self.subscription is not None or self.user.is_superuser

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

    status = models.CharField(
        max_length=20,
        choices=BlogPostStatus.choices,
        default=BlogPostStatus.DRAFT,
    )

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("blog_post", kwargs={"slug": self.slug})


class Project(BaseModel):
    profile = models.ForeignKey(Profile, null=True, blank=True, on_delete=models.CASCADE, related_name="projects")
    url = models.URLField(max_length=200, unique=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50, choices=ProjectType.choices, default=ProjectType.SAAS)
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
    competitors_list = models.TextField(blank=True)
    style = models.CharField(max_length=50, choices=ProjectStyle.choices, default=ProjectStyle.DIGITAL_ART)
    proposed_keywords = models.TextField(blank=True)

    def __str__(self):
        return self.name

    @property
    def project_details(self):
        return ProjectDetails(
            name=self.name,
            type=self.type,
            summary=self.summary,
            blog_theme=self.blog_theme,
            founders=self.founders,
            key_features=self.key_features,
            target_audience_summary=self.target_audience_summary,
            pain_points=self.pain_points,
            product_usage=self.product_usage,
            links=self.links,
            language=self.language,
            proposed_keywords=self.proposed_keywords,
        )

    @property
    def liked_title_suggestions(self):
        return self.blog_post_title_suggestions.filter(user_score__gt=0).all()

    @property
    def disliked_title_suggestions(self):
        return self.blog_post_title_suggestions.filter(user_score__lt=0).all()

    @property
    def neutral_title_suggestions(self):
        return self.blog_post_title_suggestions.filter(user_score=0).all()

    @property
    def has_pricing_page(self):
        return ProjectPage.objects.filter(project=self, type=ProjectPageType.PRICING).exists()

    def get_page_content(self):
        """
        Fetch page content using Jina Reader API and update the project.
        Returns the content if successful, raises ValueError otherwise.
        """
        html_content = get_html_content(self.url)
        title, description, markdown_content = get_markdown_content(self.url)

        if not markdown_content:
            logger.error(
                "[Get Page Content] Failed to get page content",
                title=title,
                description=description,
                markdown_content=markdown_content,
                url=self.url,
            )
            return False

        self.date_scraped = timezone.now()
        self.title = title
        self.description = description
        self.markdown_content = markdown_content
        self.html_content = html_content

        self.save(
            update_fields=[
                "date_scraped",
                "title",
                "description",
                "markdown_content",
                "html_content",
            ]
        )

        return True

    def analyze_content(self):
        """
        Analyze the page content using PydanticAI and update project details.
        Should be called after get_page_content().
        """
        agent = Agent(
            "google-gla:gemini-2.5-flash-preview-04-17",
            output_type=ProjectDetails,
            deps_type=WebPageContent,
            system_prompt=(
                "You are an expert content analyzer. Based on the web page content provided, "
                "extract and infer the requested information. Make reasonable inferences based "
                "on available content, context, and industry knowledge."
            ),
            retries=2,
        )

        @agent.system_prompt
        def add_webpage_content(ctx: RunContext[WebPageContent]) -> str:
            return (
                "Web page content:"
                f"Title: {ctx.deps.title}"
                f"Description: {ctx.deps.description}"
                f"Content: {ctx.deps.markdown_content}"
                f"HTML Content: {ctx.deps.html_content}"
            )

        result = run_agent_synchronously(
            agent,
            "Please analyze this web page content and extract the key information.",
            deps=WebPageContent(
                title=self.title,
                description=self.description,
                markdown_content=self.markdown_content,
                html_content=self.html_content,
            ),
            function_name="analyze_content",
            model_name="Project",
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
        self.language = result.data.language
        self.proposed_keywords = result.data.proposed_keywords
        self.date_analyzed = timezone.now()
        self.save()

        async_task("core.tasks.generate_blog_post_suggestions", self.id)
        async_task("core.tasks.process_project_keywords", self.id)
        async_task("core.tasks.schedule_project_page_analysis", self.id)
        async_task("core.tasks.schedule_project_competitor_analysis", self.id, timeout=180)

        return True

    def generate_title_suggestions(self, content_type=ContentType.SHARING, num_titles=3, user_prompt=""):
        agent = Agent(
            "google-gla:gemini-2.5-flash-preview-04-17",
            output_type=TitleSuggestions,
            deps_type=TitleSuggestionContext,
            system_prompt=TITLE_SUGGESTION_SYSTEM_PROMPTS[content_type],
            retries=2,
        )

        @agent.system_prompt
        def add_todays_date() -> str:
            return f"Today's Date: {timezone.now().strftime('%Y-%m-%d')}"

        @agent.system_prompt
        def add_project_details(ctx: RunContext[TitleSuggestionContext]) -> str:
            project = ctx.deps.project_details
            return f"""
                Project Details:
                - Project Name: {project.name}
                - Project Type: {project.type}
                - Project Summary: {project.summary}
                - Blog Theme: {project.blog_theme}
                - Founders: {project.founders}
                - Key Features: {project.key_features}
                - Target Audience: {project.target_audience_summary}
                - Pain Points: {project.pain_points}
                - Product Usage: {project.product_usage}
            """

        @agent.system_prompt
        def add_number_of_titles_to_generate(ctx: RunContext[TitleSuggestionContext]) -> str:
            return f"""IMPORTANT: Generate only {ctx.deps.num_titles} titles."""

        @agent.system_prompt
        def add_language_specification(ctx: RunContext[TitleSuggestionContext]) -> str:
            project = ctx.deps.project_details
            return f"""
                IMPORTANT: Generate all titles in {project.language} language.
                Make sure the titles are grammatically correct and culturally appropriate for {project.language}-speaking audiences.
            """

        @agent.system_prompt
        def add_user_prompt(ctx: RunContext[TitleSuggestionContext]) -> str:
            if not ctx.deps.user_prompt:
                return ""

            return f"""
                IMPORTANT USER REQUEST: The user has specifically requested the following:
                "{ctx.deps.user_prompt}"

                This is a high-priority requirement. Make sure to incorporate this guidance
                when generating titles while still maintaining SEO best practices and readability.
            """

        @agent.system_prompt
        def add_feedback_history(ctx: RunContext[TitleSuggestionContext]) -> str:
            # Build the feedback sections only if they exist
            feedback_sections = []

            if ctx.deps.neutral_suggestions:
                neutral = "\n".join(f"- {title}" for title in ctx.deps.neutral_suggestions)
                feedback_sections.append(
                    f"""
                    Title Suggestions that users have not yet liked or disliked:
                    {neutral}
                """
                )

            if ctx.deps.liked_suggestions:
                liked = "\n".join(f"- {title}" for title in ctx.deps.liked_suggestions)
                feedback_sections.append(
                    f"""
                    Liked Title Suggestions:
                    {liked}
                """
                )

            if ctx.deps.disliked_suggestions:
                disliked = "\n".join(f"- {title}" for title in ctx.deps.disliked_suggestions)
                feedback_sections.append(
                    f"""
                    Disliked Title Suggestions:
                    {disliked}
                """
                )

            # Add guidance only if we have any feedback
            if feedback_sections:
                feedback_sections.append(
                    """
                    Use this feedback to guide your title generation. Create titles similar to liked ones
                    and avoid patterns seen in disliked ones. Make sure to not repeat any of the titles.
                    Come up with some new ideas.
                """
                )

            return "\n".join(feedback_sections)

        deps = TitleSuggestionContext(
            project_details=self.project_details,
            num_titles=num_titles,
            user_prompt=user_prompt,
            liked_suggestions=[suggestion.title for suggestion in self.liked_title_suggestions],
            disliked_suggestions=[suggestion.title for suggestion in self.disliked_title_suggestions],
            neutral_suggestions=[suggestion.title for suggestion in self.neutral_title_suggestions],
        )

        result = run_agent_synchronously(
            agent,
            "Please generate blog post title suggestions based on the project details.",
            deps=deps,
            function_name="generate_title_suggestions",
            model_name="Project",
        )

        with transaction.atomic():
            suggestions = []
            for title in result.data.titles:
                suggestion = BlogPostTitleSuggestion(
                    project=self,
                    title=title.title,
                    description=title.description,
                    category=title.category,
                    content_type=content_type,
                    target_keywords=title.target_keywords,
                    prompt=user_prompt,
                    suggested_meta_description=title.suggested_meta_description,
                )
                suggestions.append(suggestion)

            return BlogPostTitleSuggestion.objects.bulk_create(suggestions)

    def get_a_list_of_links(self):
        agent = Agent(
            "google-gla:gemini-2.5-flash-preview-04-17",
            output_type=list[str],
            system_prompt="You are an expert link extractor. Extract all the links from the text provided.",
            retries=2,
        )

        @agent.system_prompt
        def add_links(ctx: RunContext[list[str]]) -> str:
            return f"Links: {ctx.deps}"

        result = run_agent_synchronously(
            agent,
            "Please extract all the links from the text provided.",
            deps=self.links,
            function_name="get_a_list_of_links",
            model_name="Project",
        )

        return result.data

    def find_competitors(self):
        model = OpenAIModel(
            "sonar",
            provider=OpenAIProvider(
                base_url="https://api.perplexity.ai",
                api_key=settings.PERPLEXITY_API_KEY,
            ),
        )
        agent = Agent(
            model,
            deps_type=ProjectDetails,
            output_type=str,
            system_prompt="You are a helpful assistant that helps me find competitors for my project.",
            retries=2,
        )

        @agent.system_prompt
        def add_project_details(ctx: RunContext[ProjectDetails]) -> str:
            project = ctx.deps
            return f"""I'm working on a project which has the following attributes:
                Name:
                {project.name}

                Summary:
                {project.summary}

                Key Features:
                {project.key_features}

                Target Audience:
                {project.target_audience_summary}

                Pain Points Addressed:
                {project.pain_points}

                Language: {project.language}
            """

        @agent.system_prompt
        def required_data() -> str:
            return "Make sure that each competitor has a name, url, and description."

        @agent.system_prompt
        def number_of_competitors() -> str:
            return "Give me a list of at least 15 competitors."

        @agent.system_prompt
        def language_specification() -> str:
            return (
                f"IMPORTANT: Be mindful that competitors are likely to be in {self.project_details.language} language."
            )

        result = run_agent_synchronously(
            agent,
            "Give me a list of sites that might be considered my competition.",
            deps=self.project_details,
            function_name="find_competitors",
            model_name="Project",
        )

        self.competitors_list = result.data
        self.save(update_fields=["competitors_list"])

        return result.data

    def get_and_save_list_of_competitors(self):
        agent = Agent(
            "google-gla:gemini-2.5-flash-preview-04-17",
            output_type=list[CompetitorDetails],
            system_prompt="You are an expert data extractor. Extract all the data from the text provided.",
            retries=2,
        )

        @agent.system_prompt
        def add_competitors(ctx: RunContext[list[CompetitorDetails]]) -> str:
            return f"Here are the competitors: {ctx.deps}"

        result = run_agent_synchronously(
            agent,
            "Please extract all the competitors from the text provided.",
            deps=self.competitors_list,
            function_name="get_and_save_list_of_competitors",
            model_name="Project",
        )

        competitors = []
        for competitor in result.data:
            competitors.append(
                Competitor(
                    project=self,
                    name=competitor.name,
                    url=competitor.url,
                    description=competitor.description,
                )
            )

        competitors = Competitor.objects.bulk_create(competitors)

        return competitors


class BlogPostTitleSuggestion(BaseModel):
    project = models.ForeignKey(
        Project,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="blog_post_title_suggestions",
    )

    title = models.CharField(max_length=255)
    content_type = models.CharField(max_length=20, choices=ContentType.choices, default=ContentType.SHARING)
    category = models.CharField(max_length=50, choices=Category.choices, default=Category.GENERAL_AUDIENCE)
    description = models.TextField()
    prompt = models.TextField(blank=True)
    target_keywords = models.JSONField(default=list, blank=True, null=True)
    suggested_meta_description = models.TextField(blank=True)

    user_score = models.SmallIntegerField(
        default=0,
        choices=[
            (-1, "Didn't Like"),
            (0, "Undecided"),
            (1, "Liked"),
        ],
        help_text="User's rating of the title suggestion",
    )

    archived = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.project.name}: {self.title}"

    @property
    def title_suggestion(self):
        return TitleSuggestion(
            title=self.title,
            category=self.category,
            target_keywords=self.target_keywords,
            description=self.description,
            suggested_meta_description=self.suggested_meta_description,
        )

    def generate_content(self, content_type=ContentType.SHARING):
        """
        Generate blog post content based on the title suggestion and content type.

        Args:
            content_type: The type of content to generate (SEO or SHARING)

        Returns:
            The generated blog post
        """
        agent = Agent(
            "google-gla:gemini-2.5-flash-preview-04-17",
            output_type=BlogPostContent,
            deps_type=BlogPostGenerationContext,
            system_prompt=GENERATE_CONTENT_SYSTEM_PROMPTS[content_type],
            retries=2,
            model_settings={"max_tokens": 8192, "temperature": 0.4},
        )

        @agent.system_prompt
        def add_todays_date() -> str:
            return f"Today's Date: {timezone.now().strftime('%Y-%m-%d')}"

        @agent.system_prompt
        def add_project_details(ctx: RunContext[BlogPostGenerationContext]) -> str:
            project = ctx.deps.project_details
            return f"""
                Project Details:
                - Project Name: {project.name}
                - Project Type: {project.type}
                - Project Summary: {project.summary}
                - Blog Theme: {project.blog_theme}
                - Founders: {project.founders}
                - Key Features: {project.key_features}
                - Target Audience: {project.target_audience_summary}
                - Pain Points: {project.pain_points}
                - Product Usage: {project.product_usage}
            """

        @agent.system_prompt
        def add_project_pages(ctx: RunContext[BlogPostGenerationContext]) -> str:
            pages = ctx.deps.project_pages
            if pages:
                instruction = """
                  Below is the list of page this project has. Can you insert them into
                  the content you are about to generate where it makes sense.\n
                """
                for page in pages:
                    instruction += f"""
                      --------
                      - Title: {page.title}
                      - URL: {page.url}
                      - Description: {page.description}
                      - Summary: {page.summary}
                      --------
                    """
                return instruction
            else:
                return ""

        @agent.system_prompt
        def add_title_details(ctx: RunContext[BlogPostGenerationContext]) -> str:
            title = ctx.deps.title_suggestion
            return f"""
                Title Information:
                - Title: {title.title}
                - Description: {title.description}
                - Category: {title.category}
                - Target Keywords: {', '.join(title.target_keywords) if title.target_keywords else "None specified"}
                - Suggested Meta Description: {title.suggested_meta_description if title.suggested_meta_description else "None specified"}
            """

        @agent.system_prompt
        def add_language_specification(ctx: RunContext[BlogPostGenerationContext]) -> str:
            return f"""
                IMPORTANT: Generate the content in {ctx.deps.project_details.language} language.
                Make sure the content is grammatically correct and culturally appropriate for {ctx.deps.project_details.language}-speaking audiences.
            """

        @agent.system_prompt
        def valid_markdown_format() -> str:
            return """
                IMPORTANT: Generate the content in valid markdown format.
                Make sure the content is formatted correctly with headings, paragraphs, and lists and links.
            """

        @agent.system_prompt
        def post_structure() -> str:
            return """
                - Don't include blogpost title in the content.
                - Don't start with a header or a subheader. Start with plain text as intro, then add subheaders as you see fit.
            """

        project_pages = [
            ProjectPageContext(
                url=page.url,
                title=page.title,
                description=page.description,
                summary=page.summary,
            )
            for page in self.project.project_pages.all()
        ]

        deps = BlogPostGenerationContext(
            project_details=self.project.project_details,
            title_suggestion=self.title_suggestion,
            project_pages=project_pages,
            content_type=content_type,
        )

        result = run_agent_synchronously(
            agent,
            "Please generate an article based on the project details and title suggestions.",
            deps=deps,
            function_name="generate_content",
            model_name="BlogPostTitleSuggestion",
        )

        return GeneratedBlogPost.objects.create(
            project=self.project,
            title=self,
            description=result.data.description,
            slug=result.data.slug,
            tags=result.data.tags,
            content=result.data.content,
        )


class AutoSubmittionSetting(BaseModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="auto_submittion_settings")
    endpoint_url = models.URLField(
        max_length=500, help_text="The endpoint to which posts will be automatically submitted."
    )
    body = models.JSONField(default=dict, blank=True, null=True, help_text="Key-value pairs for the request body.")
    header = models.JSONField(default=dict, blank=True, null=True, help_text="Key-value pairs for the request headers.")
    posts_per_month = models.PositiveIntegerField(default=1, help_text="How many posts to publish per month.")
    preferred_timezone = models.CharField(
        max_length=64, blank=True, null=True, help_text="Preferred timezone for publishing posts."
    )
    preferred_time = models.TimeField(blank=True, null=True, help_text="Preferred time of day to publish posts.")

    def __str__(self):
        return f"{self.project.name}"


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

    posted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.project.name}: {self.title.title}"

    @property
    def post_title(self):
        return self.title.title

    def submit_blog_post_to_endpoint(self):
        project = self.project
        settings = AutoSubmittionSetting.objects.filter(project=project).order_by("-id").first()
        if not settings or not settings.endpoint_url:
            logger.warning("No AutoSubmittionSetting or endpoint_url found for project", project_id=project.id)
            return False

        url = settings.endpoint_url
        headers = replace_placeholders(settings.header, self)
        body = replace_placeholders(settings.body, self)

        try:
            response = requests.post(url, json=body, headers=headers, timeout=15)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error("Failed to submit blog post to endpoint", error=str(e), url=url, body=body, headers=headers)
            return False


class ProjectPage(BaseModel):
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.CASCADE, related_name="project_pages")

    url = models.URLField(max_length=200)
    html_content = models.TextField(blank=True, default="")

    # Content from Jina Reader
    date_scraped = models.DateTimeField(null=True, blank=True)
    title = models.CharField(max_length=500, blank=True, default="")
    description = models.TextField(blank=True, default="")
    markdown_content = models.TextField(blank=True, default="")

    # AI Content
    date_analyzed = models.DateTimeField(null=True, blank=True)
    type = models.CharField(max_length=255, choices=ProjectPageType.choices, blank=True, default="")
    type_ai_guess = models.CharField(max_length=255)
    summary = models.TextField(blank=True)

    def __str__(self):
        return f"{self.project.name}: {self.title}"

    class Meta:
        unique_together = ("project", "url", "type")

    @property
    def web_page_content(self):
        return WebPageContent(
            title=self.title,
            description=self.description,
            markdown_content=self.markdown_content,
        )

    def get_page_content(self):
        """
        Fetch page content using Jina Reader API and update the project.
        Returns the content if successful, raises ValueError otherwise.
        """
        html_content = get_html_content(self.url)
        title, description, markdown_content = get_markdown_content(self.url)

        if not title or not description or not markdown_content:
            return False

        self.date_scraped = timezone.now()
        self.title = title
        self.description = description
        self.markdown_content = markdown_content
        self.html_content = html_content

        self.save(
            update_fields=[
                "date_scraped",
                "title",
                "description",
                "markdown_content",
                "html_content",
            ]
        )

        return True

    def analyze_content(self):
        """
        Analyze the page content using Claude via PydanticAI and update project details.
        Should be called after get_page_content().
        """
        agent = Agent(
            "google-gla:gemini-2.5-flash-preview-04-17",
            output_type=ProjectPageDetails,
            deps_type=WebPageContent,
            system_prompt=(
                "You are an expert content analyzer. Based on the web page content provided, "
                "extract and infer the requested information. Make reasonable inferences based "
                "on available content, context, and industry knowledge."
            ),
            retries=2,
        )

        @agent.system_prompt
        def add_webpage_content(ctx: RunContext[WebPageContent]) -> str:
            return (
                "Web page content:"
                f"Title: {ctx.deps.title}"
                f"Description: {ctx.deps.description}"
                f"Content: {ctx.deps.markdown_content}"
            )

        result = run_agent_synchronously(
            agent,
            "Please analyze this web page.",
            deps=WebPageContent(
                title=self.title,
                description=self.description,
                markdown_content=self.markdown_content,
                html_content=self.html_content,
            ),
            function_name="analyze_content",
            model_name="ProjectPage",
        )

        self.date_analyzed = timezone.now()

        if self.type == "":
            self.type = result.data.type

        self.type_ai_guess = result.data.type_ai_guess
        self.summary = result.data.summary
        self.save(
            update_fields=[
                "date_analyzed",
                "type",
                "type_ai_guess",
                "summary",
            ]
        )

        return True

    def create_new_pricing_strategy(self, strategy_name: str = "Alex Hormozi", user_prompt: str = ""):
        agent = Agent(
            "google-gla:gemini-2.5-flash-preview-04-17",
            output_type=PricingPageStrategySuggestion,
            deps_type=PricingPageStrategyContext,
            system_prompt=PRICING_PAGE_STRATEGY_SYSTEM_PROMPT[strategy_name],
            retries=2,
        )

        @agent.system_prompt
        def add_webpage_content(ctx: RunContext[PricingPageStrategyContext]) -> str:
            return "Pricing page content:" f"Content: {ctx.deps.web_page_content.markdown_content}"

        @agent.system_prompt
        def add_project_context(ctx: RunContext[PricingPageStrategyContext]) -> str:
            return f"""
                Project Context:
                - Project Name: {self.project.name}
                - Project Type: {self.project.type}
                - Project Summary: {self.project.summary}
                - Target Audience: {self.project.target_audience_summary}
                - Key Features: {self.project.key_features}
                - Pain Points: {self.project.pain_points}
            """

        @agent.system_prompt
        def actionable_advice() -> str:
            return """
                IMPORTANT:
                - Provide actionable advice that can be implemented immediately.
                - Avoid vague suggestions that are not actionable.
                - Focus on the specific needs and challenges of the target audience.
            """

        @agent.system_prompt
        def markdown_formatting() -> str:
            return """
                IMPORTANT: Make sure the output is valid markdown.
            """

        @agent.system_prompt
        def add_user_prompt(ctx: RunContext[PricingPageStrategyContext]) -> str:
            if not ctx.deps.user_prompt:
                return ""

            return f"""
                IMPORTANT USER REQUEST: The user has specifically requested to focus on the following:
                "{ctx.deps.user_prompt}"
            """

        result = run_agent_synchronously(
            agent,
            "Please analyze this pricing page and suggest a new pricing strategy.",
            deps=PricingPageStrategyContext(
                project_details=self.project.project_details,
                web_page_content=self.web_page_content,
            ),
            function_name="create_new_pricing_strategy",
            model_name="ProjectPage",
        )

        return PricingPageUpdatesSuggestion.objects.create(
            project=self.project,
            project_page=self,
            strategy_name=strategy_name,
            current_pricing_strategy=result.data.current_pricing_strategy,
            suggested_pricing_strategy=result.data.suggested_pricing_strategy,
        )


class PricingPageUpdatesSuggestion(BaseModel):
    project = models.ForeignKey(
        Project, null=True, blank=True, on_delete=models.CASCADE, related_name="pricing_page_updates"
    )
    project_page = models.ForeignKey(
        ProjectPage, null=True, blank=True, on_delete=models.CASCADE, related_name="pricing_page_updates"
    )

    strategy_name = models.CharField(max_length=255, blank=True, null=True)
    user_prompt = models.TextField(blank=True)
    current_pricing_strategy = models.TextField()
    suggested_pricing_strategy = models.TextField()

    def __str__(self):
        return f"{self.project.name}"


class Competitor(BaseModel):
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.CASCADE, related_name="competitors")
    name = models.CharField(max_length=255)
    url = models.URLField(max_length=200)
    description = models.TextField()

    date_scraped = models.DateTimeField(null=True, blank=True)
    homepage_title = models.CharField(max_length=500, blank=True, default="")
    homepage_description = models.TextField(blank=True, default="")
    markdown_content = models.TextField(blank=True)
    summary = models.TextField(blank=True)

    date_analyzed = models.DateTimeField(null=True, blank=True)
    # how does this competitor compare to the project?
    competitor_analysis = models.TextField(blank=True)
    key_differences = models.TextField(blank=True)
    strengths = models.TextField(blank=True)
    weaknesses = models.TextField(blank=True)
    opportunities = models.TextField(blank=True)
    threats = models.TextField(blank=True)
    key_features = models.TextField(blank=True)
    key_benefits = models.TextField(blank=True)
    key_drawbacks = models.TextField(blank=True)
    links = models.JSONField(default=list, blank=True, null=True)

    def __str__(self):
        return f"{self.name}"

    @property
    def competitor_details(self):
        return CompetitorDetails(
            name=self.name,
            url=self.url,
            description=self.description,
        )

    def get_page_content(self):
        """
        Fetch page content using Jina Reader API and update the project.
        Returns the content if successful, raises ValueError otherwise.
        """
        homepage_title, homepage_description, markdown_content = get_markdown_content(self.url)

        if not homepage_title or not homepage_description or not markdown_content:
            return False

        self.date_scraped = timezone.now()
        self.homepage_title = homepage_title
        self.homepage_description = homepage_description
        self.markdown_content = markdown_content

        self.save(
            update_fields=[
                "date_scraped",
                "homepage_title",
                "homepage_description",
                "markdown_content",
            ]
        )

        return True

    def populate_name_description(self):
        agent = Agent(
            "google-gla:gemini-2.5-flash-preview-04-17",
            output_type=CompetitorDetails,
            deps_type=WebPageContent,
            system_prompt=(
                "You are an expert marketer. Based on the competitor details and homepage content provided, "
                "extract and infer the requested information. Make reasonable inferences based "
                "on available content, context, and industry knowledge."
            ),
            retries=2,
        )

        @agent.system_prompt
        def add_webpage_content(ctx: RunContext[WebPageContent]) -> str:
            return f"Web page content:" f"Content: {ctx.deps.markdown_content}"

        deps = WebPageContent(
            title=self.homepage_title,
            description=self.homepage_description,
            markdown_content=self.markdown_content,
        )
        result = run_agent_synchronously(
            agent,
            "Please analyze this competitor and extract the key information.",
            deps=deps,
            function_name="populate_name_description",
            model_name="Competitor",
        )

        self.name = result.data.name
        self.description = result.data.description
        self.save(update_fields=["name", "description"])

        return True

    def analyze_competitor(self):
        agent = Agent(
            "google-gla:gemini-2.5-flash-preview-04-17",
            output_type=CompetitorAnalysis,
            deps_type=CompetitorAnalysisContext,
            system_prompt=(
                "You are an expert marketer. Based on the competitor details and homepage content provided, "
                "extract and infer the requested information. Make reasonable inferences based "
                "on available content, context, and industry knowledge."
            ),
            retries=2,
        )

        @agent.system_prompt
        def add_todays_date() -> str:
            return f"Today's Date: {timezone.now().strftime('%Y-%m-%d')}"

        @agent.system_prompt
        def my_project_details(ctx: RunContext[CompetitorAnalysisContext]) -> str:
            project = ctx.deps.project_details
            return f"""
                Project Details:
                - Project Name: {project.name}
                - Project Type: {project.type}
                - Project Summary: {project.summary}
                - Blog Theme: {project.blog_theme}
                - Founders: {project.founders}
                - Key Features: {project.key_features}
                - Target Audience: {project.target_audience_summary}
                - Pain Points: {project.pain_points}
                - Product Usage: {project.product_usage}
            """

        @agent.system_prompt
        def competitor_details(ctx: RunContext[CompetitorAnalysisContext]) -> str:
            competitor = ctx.deps.competitor_details
            return f"""
                Competitor Details:
                - Competitor Name: {competitor.name}
                - Competitor URL: {competitor.url}
                - Competitor Description: {competitor.description}
                - Competitor Homepage Content: {ctx.deps.competitor_homepage_content}
            """

        deps = CompetitorAnalysisContext(
            project_details=self.project.project_details,
            competitor_details=self.competitor_details,
            competitor_homepage_content=self.markdown_content,
        )
        result = run_agent_synchronously(
            agent,
            "Please analyze this competitor and extract the key information.",
            deps=deps,
            function_name="analyze_competitor",
            model_name="Competitor",
        )

        self.competitor_analysis = result.data.competitor_analysis
        self.key_differences = result.data.key_differences
        self.strengths = result.data.strengths
        self.summary = result.data.summary
        self.weaknesses = result.data.weaknesses
        self.opportunities = result.data.opportunities
        self.threats = result.data.threats
        self.key_features = result.data.key_features
        self.key_benefits = result.data.key_benefits
        self.key_drawbacks = result.data.key_drawbacks
        self.links = result.data.links
        self.date_analyzed = timezone.now()
        self.save()

        return True


class CompetitorComparisonBlogPost(BaseModel):
    project = models.ForeignKey(
        Project, null=True, blank=True, on_delete=models.CASCADE, related_name="competitor_comparison_blog_posts"
    )
    competitor = models.ForeignKey(
        Competitor, null=True, blank=True, on_delete=models.CASCADE, related_name="competitor_comparison_blog_posts"
    )

    title = models.CharField(max_length=255)
    description = models.TextField()
    slug = models.SlugField(max_length=250)
    content = models.TextField()

    def __str__(self):
        return f"{self.project.name}: {self.title}"


class Keyword(BaseModel):
    keyword_text = models.CharField(max_length=255, help_text="The keyword string")
    volume = models.IntegerField(null=True, blank=True, help_text="The search volume of the keyword")
    cpc_currency = models.CharField(max_length=10, blank=True, help_text="The currency of the CPC value")
    cpc_value = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, help_text="The cost per click value"
    )
    competition = models.FloatField(null=True, blank=True, help_text="The competition metric of the keyword (0 to 1)")
    country = models.CharField(
        max_length=10, blank=True, default="us", help_text="The country for which metrics were fetched"
    )
    data_source = models.CharField(
        max_length=3,
        choices=KeywordDataSource.choices,
        default=KeywordDataSource.GOOGLE_KEYWORD_PLANNER,
        blank=True,
        help_text="The data source for the keyword metrics",
    )
    last_fetched_at = models.DateTimeField(auto_now=True, help_text="Timestamp of when the data was last fetched")

    class Meta:
        unique_together = ("keyword_text", "country", "data_source")
        verbose_name = "Keyword"
        verbose_name_plural = "Keywords"

    def __str__(self):
        return f"{self.keyword_text} ({self.country or 'global'} - {self.data_source or 'N/A'})"

    def fetch_and_update_metrics(self, currency="usd"):
        if not hasattr(settings, "KEYWORDS_EVERYWHERE_API_KEY"):
            logger.error("[KeywordFetch] KEYWORDS_EVERYWHERE_API_KEY not found in settings.")
            return False

        api_key = settings.KEYWORDS_EVERYWHERE_API_KEY
        api_url = "https://api.keywordseverywhere.com/v1/get_keyword_data"

        payload = {
            "kw[]": [self.keyword_text],
            "country": self.country,
            "currency": currency,
            "dataSource": self.data_source,
        }
        headers = {"Accept": "application/json", "Authorization": f"Bearer {api_key}"}

        try:
            response = requests.post(api_url, data=payload, headers=headers, timeout=30)
            response.raise_for_status()  # Raises HTTPError for bad responses (4XX or 5XX)

            response_data = response.json()

            if (
                not response_data.get("data")
                or not isinstance(response_data["data"], list)
                or not response_data["data"][0]
            ):
                logger.warning(
                    "[KeywordFetch] No data found in API response for keyword.",
                    keyword_id=self.id,
                    keyword_text=self.keyword_text,
                    response_status=response.status_code,
                    response_content=response.text[:500],
                )
                return False

            keyword_api_data = response_data["data"][0]

            self.volume = keyword_api_data.get("vol")

            cpc_data = keyword_api_data.get("cpc", {})
            self.cpc_currency = cpc_data.get("currency", "")
            try:
                self.cpc_value = Decimal(str(cpc_data.get("value", "0.00")))
            except InvalidOperation:
                logger.warning(
                    f"[KeywordFetch] Invalid CPC value for keyword {self.keyword_text}. Defaulting to 0.00.",
                    keyword_id=self.id,
                    cpc_value_raw=cpc_data.get("value"),
                )
                self.cpc_value = Decimal("0.00")

            self.competition = keyword_api_data.get("competition")
            self.last_fetched_at = timezone.now()

            # Save keyword instance before handling trends to ensure FK exists
            self.save(update_fields=["volume", "cpc_currency", "cpc_value", "competition", "last_fetched_at"])

            trend_data = keyword_api_data.get("trend", [])
            if isinstance(trend_data, list):
                with transaction.atomic():
                    # Get a set of existing (month, year) tuples for efficient lookup
                    existing_trends_tuples = set(self.trends.values_list("month", "year"))

                    trends_to_create = []
                    for trend_item in trend_data:
                        if (
                            isinstance(trend_item, dict)
                            and "month" in trend_item
                            and "year" in trend_item
                            and "value" in trend_item
                        ):
                            month_str = str(trend_item["month"])
                            year_int = int(trend_item["year"])

                            # Check if this month/year combo already exists
                            if (month_str, year_int) not in existing_trends_tuples:
                                trends_to_create.append(
                                    KeywordTrend(
                                        keyword=self, month=month_str, year=year_int, value=int(trend_item["value"])
                                    )
                                )
                    if trends_to_create:
                        KeywordTrend.objects.bulk_create(trends_to_create)

            logger.info(
                "[KeywordFetch] Successfully fetched and updated metrics.",
                keyword_id=self.id,
                keyword_text=self.keyword_text,
            )
            return True

        except requests.exceptions.HTTPError as e:
            logger.error(
                "[KeywordFetch] HTTP error occurred.",
                keyword_id=self.id,
                keyword_text=self.keyword_text,
                error=str(e),
                status_code=e.response.status_code if e.response else None,
                response_content=e.response.text[:500] if e.response else None,
            )
            # Specific handling for API error codes
            if e.response is not None:
                if e.response.status_code == 401:
                    logger.error("[KeywordFetch] API Key is missing or invalid.")
                elif e.response.status_code == 402:
                    logger.error("[KeywordFetch] Insufficient credits or invalid subscription.")
                elif e.response.status_code == 400:
                    logger.error("[KeywordFetch] Submitted request data is invalid.")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(
                "[KeywordFetch] Request exception occurred.",
                keyword_id=self.id,
                keyword_text=self.keyword_text,
                error=str(e),
            )
            return False
        except Exception as e:
            logger.error(
                "[KeywordFetch] An unexpected error occurred.",
                keyword_id=self.id,
                keyword_text=self.keyword_text,
                error=str(e),
            )
            return False


class ProjectKeyword(BaseModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="project_keywords")
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE, related_name="keyword_projects")
    use = models.BooleanField(default=False)
    date_associated = models.DateTimeField(
        auto_now_add=True, help_text="When the keyword was associated with the project"
    )

    class Meta:
        unique_together = ("project", "keyword")
        verbose_name = "Project Keyword"
        verbose_name_plural = "Project Keywords"

    def __str__(self):
        return f"{self.project.name} - {self.keyword.keyword_text}"


class KeywordTrend(BaseModel):
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE, related_name="trends")
    month = models.CharField(max_length=10, help_text="The month of this volume (e.g., May)")
    year = models.IntegerField(help_text="The year of this volume (e.g., 2019)")
    value = models.IntegerField(help_text="The search volume of the keyword for the given month")

    class Meta:
        unique_together = ("keyword", "month", "year")
        verbose_name = "Keyword Trend"
        verbose_name_plural = "Keyword Trends"
        ordering = ["keyword", "year", "month"]

    def __str__(self):
        return f"{self.keyword.keyword_text} - {self.month} {self.year}: {self.value}"


class Feedback(BaseModel):
    profile = models.ForeignKey(Profile, null=True, blank=True, on_delete=models.CASCADE, related_name="feedback")
    feedback = models.TextField()
    page = models.CharField(max_length=255)
    date_submitted = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.profile.user.email}: {self.feedback}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)

        if is_new:
            from django.conf import settings
            from django.core.mail import send_mail

            subject = "New Feedback Submitted"
            message = f"New feedback was submitted:\n\nUser: {self.profile.user.email if self.profile else 'Anonymous'}\nFeedback: {self.feedback}\nPage: {self.page}"
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = ["kireevr1996@gmail.com"]

            send_mail(subject, message, from_email, recipient_list, fail_silently=True)
