from pydantic import BaseModel, Field


class ProjectAnalysis(BaseModel):
    name: str = Field(
        description="""
        Official registered name of the project, company, or organization
    """
    )
    type: str = Field(
        description="""
        Primary business model or project category
        (e.g., SaaS, Ecommerce, Marketplace, Mobile App, B2B Service)
    """
    )
    summary: str = Field(
        description="""
        Detailed 4-5 sentence overview that should include:
        1) The core purpose and mission of the project,
        2) The main value proposition and what makes it unique,
        3) How it specifically serves its users and improves their lives/work,
        4) The key problem it solves and why its approach is effective,
        5) Any notable achievements, market position, or distinguishing characteristics.
        Focus on clarity and concrete details rather than marketing language.
    """
    )
    blog_theme: str = Field(
        description="""
        Comprehensive semicolon-separated list of content themes that should include:
        1) Primary topic areas aligned with product features,
        2) Industry trends and developments relevant to users,
        3) Educational content that showcases expertise,
        4) User success stories and use cases,
        5) Technical topics and how-to guides,
        6) Thought leadership areas.
        Each theme should be specific and actionable, not generic.
        Example: 'DevOps automation best practices; Container orchestration deep dives;
        Cloud cost optimization strategies; Team collaboration techniques'
    """
    )
    founders: str = Field(
        description="""
        Semicolon-separated list of founders with their full names and current roles/positions in the project.
        Format: 'Name - Role'
    """
    )
    key_features: str = Field(
        description="""
        Detailed semicolon-separated list of product capabilities that should include:
        1) Core functionalities that solve primary user problems,
        2) Unique technological innovations or approaches,
        3) Integration capabilities and ecosystem connections,
        4) Automation and efficiency features,
        5) Customization and flexibility options,
        6) Security and compliance features,
        7) Scalability aspects.
        Each feature should be described with specific
        benefits and outcomes, not just feature names.
    """
    )
    target_audience_summary: str = Field(
        description="""
        Comprehensive profile of ideal users that should detail:
        1) Demographic information including job roles, industry sectors, and company sizes,
        2) Technical expertise level and tool familiarity,
        3) Daily challenges and responsibilities in their work,
        4) Decision-making authority and purchasing power,
        5) Goals and success metrics they care about,
        6) Common workflows and processes they manage,
        7) Team structure and collaboration patterns. Paint a clear picture of who the user is and their context.
    """
    )
    pain_points: str = Field(
        description="""
        Detailed semicolon-separated list of specific challenges that should include:
        1) Technical problems faced in daily operations,
        2) Process inefficiencies and bottlenecks,
        3) Resource constraints and limitations,
        4) Compliance and security challenges,
        5) Integration and compatibility issues,
        6) Scaling and growth obstacles,
        7) Team collaboration difficulties.
        Each pain point should be specific and relatable to the target audience,
        with clear connection to how the product addresses it.
    """
    )
    product_usage: str = Field(
        description="""
        Comprehensive semicolon-separated list that should detail:
        1) Step-by-step workflows for common use cases,
        2) Integration scenarios with other tools and systems,
        3) Team collaboration patterns and user roles,
        4) Customization and configuration examples,
        5) Data management and processing workflows, 6) Automation and scheduling scenarios, 7) Reporting and analytics usage.
        Each usage pattern should be specific and illustrate real-world application.
    """
    )
    links: str = Field(
        description="""
        Collection of relevant URLs found on the page, including social media,
        documentation, product pages, and other important resources
    """
    )


class TitleSuggestion(BaseModel):
    title: str = Field(
        description="""
        Engaging and SEO-optimized blog post title that captures the main topic
    """
    )
    category: str = Field(
        description="""
          Primary content category or topic area that the blog post belongs to
    """
    )
    target_keywords: list[str] = Field(
        description="""
        List of strategic SEO keywords and phrases to target in the blog post for better search visibility
    """
    )
    description: str = Field(
        description="""
        Brief overview of the blog post's main topic, angle, and key points to be covered.
        Comma separated list of keywords.
    """
    )
    suggested_meta_description: str = Field(
        description="""
        SEO-optimized meta description (150-160 characters) summarizing the blog post for search engine results
    """
    )


class TitleSuggestions(BaseModel):
    titles: list[TitleSuggestion] = Field(
        description="""
        Collection of generated title suggestions with their associated metadata and SEO information
    """
    )


class BlogPostContent(BaseModel):
    description: str = Field(
        description="""Meta description (150-160 characters) that should:
        - Include primary keyword naturally (if SEO type)
        - Focus on value proposition and user intent
        - Be compelling and drive click-through
        - Maintain single line, no line breaks
        """
    )
    slug: str = Field(
        description="""URL-friendly format that should:
        - Include primary keyword if possible (if SEO type)
        - Use lowercase letters, numbers, and hyphens only
        - Be concise and readable
        - Remove special characters and spaces
        """
    )
    tags: str = Field(
        description="""5-8 keywords formatted as: "Tag 1, Tag 2, Tag 3, Tag 4, Tag 5" that:
        - Include primary and secondary keywords (if SEO type)
        - Mix short and long-tail terms
        - Focus on {{ suggestion.project.type }} industry
        - Balance general and specific terms
        """
    )
    content: str = Field(
        description="""Full blog post in Markdown format that includes:

        1. Structure:
        - Strong H1 heading (with primary keyword for SEO type)
        - Clear H2 and H3 subheadings
        - Compelling introduction (keyword in first 100 words for SEO)

        2. Content Quality:
        - Include relevant statistics and data
        - Link to authoritative sources
        - Address user intent comprehensively

        3. Readability:
        - Short paragraphs (2-3 sentences)
        - Strategic use of bullet points and lists
        - Table of contents for longer posts
        - Natural language flow

        4. Engagement:
        - Clear calls-to-action
        - Address audience pain points
        - Reference key features where relevant
        """
    )
