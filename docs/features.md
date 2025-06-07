# Marketing Agents Features

This document provides an overview of the user-facing features of the Marketing Agents application.

## Core Concepts

### Projects
A **Project** is the central entity in the application. You create a project by providing a URL to your existing website. The application then scans your website to understand your product, target audience, and existing content. This analysis forms the basis for all the marketing agent capabilities.

### Agents
The application is composed of several "Agents," each designed to automate a specific marketing task. These agents use the information from your project to generate tailored content and analysis.

---

## Feature List

### 1. Project & Website Analysis
- **Project Creation**: Users can create a new project by simply providing their website's URL. The system automatically scrapes and analyzes the homepage to understand the business.
- **Project Dashboard**: A central place to view all your projects and their high-level status.
- **Detailed Project Analysis**: The system extracts key information about your project, including:
    - Key Features
    - Target Audience
    - Customer Pain Points
    - Product Usage Instructions
    - Blog Themes & Founders

### 2. Blogging & Content Generation Agent
- **AI-Powered Title Suggestions**: Generate multiple blog post title ideas based on different content strategies (e.g., educational, promotional).
- **Generate Titles from an Idea**: Provide your own idea or topic, and the AI will craft a compelling title for you.
- **User Feedback on Titles**: Rate title suggestions (like/dislike) to improve future recommendations.
- **Full Blog Post Generation**: Once you've chosen a title, the agent can write an entire blog post, complete with sections, paragraphs, and formatting.
- **Automatic Content Submission**: Configure an endpoint to have your generated blog posts automatically sent to your CMS (e.g., WordPress, Ghost) for publishing.

### 3. Competitor Analysis Agent
- **Competitor Discovery**: The system can help identify potential competitors based on your project's profile.
- **Detailed Competitor Breakdown**: Add a competitor's URL, and the agent will analyze their website to provide a detailed report, including:
    - SWOT Analysis (Strengths, Weaknesses, Opportunities, Threats)
    - Key Features & Benefits
    - Comparison to your own project.
- **Competitor Comparison Blog Posts**: (Planned) Automatically generate blog posts that compare your product to a competitor's.

### 4. Keyword Research Agent
- **Keyword Discovery**: Add keywords relevant to your project to track their performance.
- **Keyword Metrics**: The system fetches key metrics for your keywords, including:
    - Search Volume
    - Cost-Per-Click (CPC)
    - Competition Level
- **Keyword Management**: Toggle which keywords you want to actively focus on for your content strategy.
- **Trend Analysis**: View historical search volume trends for your keywords.

### 5. Pricing Strategy Agent
- **Pricing Page Analysis**: Add your pricing page URL, and the agent will analyze its structure and content.
- **AI-Powered Strategy Suggestions**: Receive actionable recommendations to improve your pricing page, based on established marketing frameworks (e.g., Alex Hormozi's value-based pricing).

### 6. User Management & Billing
- **User Profile Settings**: Manage your account details.
- **Subscription Management**: Easily subscribe to a plan or manage your existing subscription through a customer portal (powered by Stripe).
- **Usage-Based Limits**: The free tier has limits on the number of title suggestions and content generations, which are removed with a subscription.
- **Feedback System**: A built-in mechanism to submit feedback directly to the development team.

---

## Planned Features

- Generation of blog posts that directly compare your project with a specified competitor.
