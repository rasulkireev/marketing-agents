# Blog Post Scheduling Documentation

This document describes the automated blog post scheduling system that checks AutoSubmissionSettings and schedules blog posts based on user-defined posting frequencies.

## Overview

The blog post scheduling system consists of three main functions:

1. `check_and_schedule_blog_posts()` - Main function that processes all AutoSubmissionSettings
2. `should_schedule_next_post()` - Determines if a blog post should be scheduled
3. `submit_scheduled_blog_post()` - Submits a scheduled blog post to its endpoint

## How It Works

### 1. AutoSubmissionSetting Processing

The system iterates through all `AutoSubmissionSetting` objects and for each:

- Checks if the associated project has any generated blog posts
- Finds the last posted blog post for that project
- Calculates if a new post should be scheduled based on the `posts_per_month` setting
- Schedules the next available unposted blog post if needed

### 2. Scheduling Logic

The scheduling logic considers:

- **Posts per month**: Converts this to days between posts (30 days / posts_per_month)
- **Preferred timezone**: Uses the project's preferred timezone or UTC as fallback
- **Preferred time**: Schedules at the specified time if set
- **Last post date**: Ensures enough time has passed since the last post

### 3. Scheduling Behavior

- **First post**: If no previous posts exist, schedules immediately or at next preferred time
- **Subsequent posts**: Schedules based on the calculated interval from the last post
- **Timezone handling**: Properly converts times to the user's preferred timezone

## Usage

### Running via Management Command

```bash
# Run the scheduling check
python manage.py schedule_blog_posts

# Run in dry-run mode (shows what would be scheduled)
python manage.py schedule_blog_posts --dry-run
```

### Running via Django-Q2

You can schedule this to run periodically using Django-Q2:

```python
from django_q.tasks import schedule

# Schedule to run every hour
schedule(
    'core.tasks.check_and_schedule_blog_posts',
    schedule_type='H',  # Hourly
    repeats=-1,  # Repeat indefinitely
)

# Schedule to run daily at 9 AM
schedule(
    'core.tasks.check_and_schedule_blog_posts',
    schedule_type='D',  # Daily
    next_run=timezone.now().replace(hour=9, minute=0, second=0, microsecond=0),
    repeats=-1,  # Repeat indefinitely
)
```

### Direct Function Call

```python
from core.tasks import check_and_schedule_blog_posts

# Run the scheduling check
result = check_and_schedule_blog_posts()
print(result)
```

## AutoSubmissionSetting Model

The system uses the following fields from the `AutoSubmissionSetting` model:

- `project`: The associated project
- `posts_per_month`: How many posts to publish per month (default: 1)
- `preferred_timezone`: Timezone for scheduling (default: UTC)
- `preferred_time`: Preferred time of day for posting
- `endpoint_url`: The endpoint to submit posts to
- `body`: JSON body template for the API request
- `header`: JSON header template for the API request

## Error Handling

The system includes comprehensive error handling:

- **Timezone errors**: Falls back to UTC if an invalid timezone is specified
- **Missing blog posts**: Logs info when no posts are available for scheduling
- **API submission errors**: Logs failures but continues processing other projects
- **Database errors**: Logs and returns error messages for debugging

## Logging

The system uses structured logging with the following information:

- Project ID and name
- Blog post ID and title
- Scheduled times
- Error messages and stack traces
- Success/failure status

## Example Scenarios

### Scenario 1: Daily Posting

```python
# AutoSubmissionSetting with posts_per_month=30
# Will schedule approximately every day
```

### Scenario 2: Weekly Posting

```python
# AutoSubmissionSetting with posts_per_month=4
# Will schedule approximately every 7.5 days
```

### Scenario 3: Monthly Posting

```python
# AutoSubmissionSetting with posts_per_month=1
# Will schedule approximately every 30 days
```

## Monitoring

You can monitor the scheduling system by:

1. **Checking Django-Q2 tasks**: Look for scheduled tasks in the "Blog Post Submission" group
2. **Reviewing logs**: Check application logs for scheduling activity
3. **Database queries**: Query `GeneratedBlogPost` for posts with `posted=True`

## Database Schema

The system works with these main models:

- `AutoSubmissionSetting`: Configuration for automatic posting
- `GeneratedBlogPost`: Blog posts with `posted` status tracking
- `Project`: Associated projects with generated blog posts

## Configuration

### Required Settings

- Django-Q2 must be properly configured
- `pytz` library must be installed for timezone handling
- API endpoints must be accessible from the application server

### Optional Settings

- Configure logging levels to adjust verbosity
- Set up monitoring for Django-Q2 task execution
- Configure error alerting for failed submissions

## Troubleshooting

### Common Issues

1. **No posts scheduled**: Check if projects have generated blog posts
2. **Timezone errors**: Ensure timezone strings are valid pytz timezone names
3. **API failures**: Check endpoint URLs and authentication in AutoSubmissionSetting
4. **Task not executing**: Verify Django-Q2 is running and configured correctly

### Debug Steps

1. Run with management command to see immediate output
2. Check Django-Q2 task queue for scheduled tasks
3. Review application logs for error messages
4. Test API endpoints manually with the configured headers/body

## Future Enhancements

Potential improvements to the system:

- Add support for different posting patterns (e.g., weekdays only)
- Implement retry logic for failed submissions
- Add email notifications for scheduling events
- Support for post categories and tagging
- Integration with social media platforms