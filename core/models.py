from django.contrib.auth.models import User
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from core.base_models import BaseModel
from core.choices import Category, ContentType, Language, ProfileStates, ProjectPageType, ProjectStyle, ProjectType
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
from seo_blog_bot import settings
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
    competitors_list = models.TextField(blank=True)
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
        self.date_analyzed = timezone.now()
        self.save()

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
            result_type=str,
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
            "google-gla:gemini-2.0-flash",
            result_type=list[CompetitorDetails],
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
            "google-gla:gemini-2.0-flash",
            result_type=PricingPageStrategySuggestion,
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
            "google-gla:gemini-2.0-flash",
            result_type=CompetitorDetails,
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
            "google-gla:gemini-2.0-flash",
            result_type=CompetitorAnalysis,
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
