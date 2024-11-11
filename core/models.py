from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse

from core.base_models import BaseModel
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
        # Add other languages as needed

    profile = models.ForeignKey(Profile, null=True, blank=True, on_delete=models.CASCADE, related_name="projects")
    url = models.URLField(max_length=200, unique=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50, choices=Type.choices, default=Type.SAAS)
    summary = models.TextField()
    blog_theme = models.TextField()
    founders = models.TextField(blank=True)
    key_features = models.TextField()
    language = models.CharField(max_length=50, choices=Language.choices, default=Language.ENGLISH)
    target_audience_summary = models.TextField()
    pain_points = models.TextField()
    product_usage = models.TextField()
    style = models.CharField(max_length=50, choices=Style.choices, default=Style.DIGITAL_ART)

    def __str__(self):
        return self.name

    def should_blur_suggestions(self):
        if not self.profile:
            return True
        # current_state = self.profile.current_state
        return False  # current_state not in [ProfileStates.SUBSCRIBED, ProfileStates.CANCELLED]


class BlogPostTitleSuggestion(BaseModel):
    project = models.ForeignKey(
        Project, null=True, blank=True, on_delete=models.CASCADE, related_name="blog_post_title_suggestions"
    )
    title = models.CharField(max_length=255)
    description = models.TextField()

    class Category(models.TextChoices):
        GENERAL_AUDIENCE = "General Audience", "General Audience"
        NICH_AUDIENCE = "Niche Audience", "Niche Audience"
        INDUSTRY_COMPANY = "Industry/Company", "Industry/Company"

    category = models.CharField(max_length=50, choices=Category.choices, default=Category.GENERAL_AUDIENCE)


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
