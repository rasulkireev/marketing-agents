from django.db import models


class ContentType(models.TextChoices):
    SHARING = "SHARING", "Sharing"
    SEO = "SEO", "SEO"


class Category(models.TextChoices):
    GENERAL_AUDIENCE = "General Audience", "General Audience"
    NICH_AUDIENCE = "Niche Audience", "Niche Audience"
    INDUSTRY_COMPANY = "Industry/Company", "Industry/Company"
