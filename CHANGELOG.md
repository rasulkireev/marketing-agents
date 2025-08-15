<!-- Types of changes -->
**Added** for new features.
**Changed** for changes in existing functionality.
**Deprecated** for soon-to-be removed features.
**Removed** for now removed features.
**Fixed** for any bug fixes.
**Security** in case of vulnerabilities.

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.0.4] - 2025-08-15
**Fixed**
- `generate_and_post_blog_post` UnboundLocalError
- UI on the user-settings page, plus issue with Update Subscription links
- UI on the login and signup pages
- Saving the Auto Posting setting


## [0.0.3] - 2025-08-10
**Removed**
- Various agents, focus on generating blog post content
- PricingPageAnalysis and CompetitorBlog post models
- Views for now unsporrted models
- Posthog Alias Creation in HomePageView

**Changed**
- Simplification of the design and the UI

**Added**
- A page for generated content

## [0.0.1] - 2025-08-09
**Added**
- Adding automated posting feature

**Fixed**
- `last_posted_blog_post` fixed when don't exist
- Schedule post if there are no posts from the past
