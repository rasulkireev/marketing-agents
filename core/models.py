from django.contrib.auth.models import User
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone
from pydantic_ai import Agent, RunContext, capture_run_messages

from core.base_models import BaseModel
from core.choices import Category, ContentType, Language, ProfileStates, ProjectPageType, ProjectStyle, ProjectType
from core.model_utils import generate_random_key, get_html_content, get_markdown_content, run_agent_synchronously
from core.prompts import GENERATE_CONTENT_SYSTEM_PROMPTS, TITLE_SUGGESTION_SYSTEM_PROMPTS
from core.schemas import (
    BlogPostContent,
    BlogPostGenerationContext,
    PricingPageStrategyContext,
    PricingPageStrategySuggestion,
    ProjectDetails,
    ProjectPageDetails,
    TitleSuggestion,
    TitleSuggestionContext,
    TitleSuggestions,
    WebPageContent,
)
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
        return self.product is not None or self.subscription is not None

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
    style = models.CharField(max_length=50, choices=ProjectStyle.choices, default=ProjectStyle.DIGITAL_ART)

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
        )

    @property
    def liked_title_suggestions(self):
        return self.blog_post_title_suggestions.filter(user_score__gt=0).all()

    @property
    def disliked_title_suggestions(self):
        return self.blog_post_title_suggestions.filter(user_score__lt=0).all()

    @property
    def has_pricing_page(self):
        return ProjectPage.objects.filter(project=self, type=ProjectPageType.PRICING).exists()

    @property
    def pricing_page(self):
        return ProjectPage.objects.filter(project=self, type=ProjectPageType.PRICING).latest("id")

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

        logger.info(
            "[Page Content] Successfully fetched content",
            project_name=self.name,
            project_url=self.url,
        )

        return True

    def analyze_content(self):
        """
        Analyze the page content using PydanticAI and update project details.
        Should be called after get_page_content().
        """
        agent = Agent(
            "google-gla:gemini-2.0-flash",
            result_type=ProjectDetails,
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
        )

        logger.info("[Analyze Content] Agent ran successfully", data=result.data)

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
        self.date_analyzed = timezone.now()
        self.save()

        logger.info("[Analyze Content] Successfully analyzed content", project_name=self.name, project_url=self.url)

        return True

    def generate_title_suggestions(self, content_type=ContentType.SHARING, num_titles=3, user_prompt=""):
        agent = Agent(
            "google-gla:gemini-2.0-flash",
            result_type=TitleSuggestions,
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
            # If there are no liked or disliked suggestions, don't add this section
            if not ctx.deps.liked_suggestions and not ctx.deps.disliked_suggestions:
                return ""

            # Build the feedback sections only if they exist
            feedback_sections = []

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
                    and avoid patterns seen in disliked ones.
                """
                )

            return "\n".join(feedback_sections)

        deps = TitleSuggestionContext(
            project_details=self.project_details,
            num_titles=num_titles,
            user_prompt=user_prompt,
            liked_suggestions=[suggestion.title for suggestion in self.liked_title_suggestions],
            disliked_suggestions=[suggestion.title for suggestion in self.disliked_title_suggestions],
        )

        result = run_agent_synchronously(
            agent, "Please generate blog post title suggestions based on the project details.", deps=deps
        )

        logger.info(
            "[Generate SEO Title Suggestions] Successfully generated titles",
            project_name=self.name,
            project_url=self.url,
            num_titles=num_titles,
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
                    suggested_meta_description=title.suggested_meta_description,
                )
                suggestions.append(suggestion)

            return BlogPostTitleSuggestion.objects.bulk_create(suggestions)

    def get_a_list_of_links(self):
        agent = Agent(
            "google-gla:gemini-2.0-flash",
            result_type=list[str],
            system_prompt="You are an expert link extractor. Extract all the links from the text provided.",
            retries=2,
        )

        @agent.system_prompt
        def add_links(ctx: RunContext[list[str]]) -> str:
            return f"Links: {ctx.deps}"

        logger.info(
            "[Get a List of Links] Running agent",
            project_name=self.name,
            project_id=self.id,
            links=self.links,
        )

        result = run_agent_synchronously(
            agent,
            "Please extract all the links from the text provided.",
            deps=self.links,
        )

        return result.data


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
            "google-gla:gemini-2.0-flash",
            result_type=BlogPostContent,
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

        deps = BlogPostGenerationContext(
            project_details=self.project.project_details,
            title_suggestion=self.title_suggestion,
            content_type=content_type,
        )

        with capture_run_messages() as messages:
            try:
                result = run_agent_synchronously(
                    agent, "Please generate an article based on the project details and title suggestions.", deps=deps
                )
            except Exception as e:
                logger.error(
                    "[Generate Content] Failed generation",
                    messages=messages,
                    exc_info=True,
                    error=str(e),
                )
                raise

        return GeneratedBlogPost.objects.create(
            project=self.project,
            title=self,
            description=result.data.description,
            slug=result.data.slug,
            tags=result.data.tags,
            content=result.data.content,
        )


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
    type = models.CharField(max_length=255, choices=ProjectPageType.choices, default=ProjectPageType.BLOG)
    type_ai_guess = models.CharField(max_length=255)
    summary = models.TextField(blank=True)

    def __str__(self):
        return f"{self.project.name}: {self.title}"

    class Meta:
        unique_together = ("project", "url")

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

        logger.info(
            "[Page Content] Successfully fetched content",
            project_name=self.project.name,
            project_url=self.url,
        )

        return True

    def analyze_content(self):
        """
        Analyze the page content using Claude via PydanticAI and update project details.
        Should be called after get_page_content().
        """
        agent = Agent(
            "google-gla:gemini-2.0-flash",
            result_type=ProjectPageDetails,
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
        )

        self.date_analyzed = timezone.now()
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

        logger.info(
            "[Analyze Content] Successfully analyzed content",
            project_name=self.title,
            project_url=self.url,
        )

        return True

    def create_new_pricing_strategy(self):
        agent = Agent(
            "google-gla:gemini-2.0-flash",
            result_type=PricingPageStrategySuggestion,
            deps_type=PricingPageStrategyContext,
            system_prompt="You are an expert pricing strategist. Based on the web page content provided, create a new pricing strategy.",
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

        result = run_agent_synchronously(
            agent,
            "Please analyze this pricing page and suggest a new pricing strategy.",
            deps=PricingPageStrategyContext(
                project_details=self.project.project_details,
                web_page_content=self.web_page_content,
            ),
        )

        logger.info(
            "[Create New Pricing Strategy] Successfully generated pricing strategy",
            project_name=self.project.name,
            project_url=self.url,
        )

        return PricingPageUpdatesSuggestion.objects.create(
            project=self.project,
            project_page=self,
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

    user_prompt = models.TextField(blank=True)
    current_pricing_strategy = models.TextField()
    suggested_pricing_strategy = models.TextField()

    def __str__(self):
        return f"{self.project.name}"
