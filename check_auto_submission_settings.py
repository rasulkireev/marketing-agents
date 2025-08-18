#!/usr/bin/env python
"""
Quick script to check your AutoSubmissionSetting configuration.
Run with: python manage.py shell -c "exec(open('check_auto_submission_settings.py').read())"
"""

import json

from core.models import AutoSubmissionSetting, GeneratedBlogPost, Profile
from core.utils import replace_placeholders

print("=== AutoSubmissionSetting Configuration Check ===")
print()

# Check all AutoSubmissionSettings
settings = AutoSubmissionSetting.objects.all()

if not settings.exists():
    print("❌ No AutoSubmissionSettings found!")
    print("   Go to your project settings to configure automatic submission.")
    exit()

for i, setting in enumerate(settings, 1):
    print(f"Setting #{i}:")
    print(f"  Project: {setting.project.name}")
    print(f"  Endpoint URL: {setting.endpoint_url}")
    print(f"  Headers: {json.dumps(setting.header, indent=2) if setting.header else 'None'}")
    print(f"  Body: {json.dumps(setting.body, indent=2) if setting.body else 'None'}")

    # Check if headers contain authorization
    if setting.header:
        has_auth = "authorization" in setting.header or "Authorization" in setting.header
        print(f"  ✅ Authorization header: {'Present' if has_auth else '❌ MISSING'}")

        if has_auth:
            auth_value = setting.header.get("authorization") or setting.header.get("Authorization")
            is_bearer = auth_value.startswith("Bearer ") if auth_value else False
            print(f"  ✅ Bearer format: {'Correct' if is_bearer else '❌ INCORRECT'}")

            if is_bearer:
                token = auth_value.split(" ")[1] if len(auth_value.split(" ")) > 1 else ""
                print(f"  Token: {token}")

                # Try to find matching profile
                try:
                    profile = Profile.objects.get(key=token)
                    print(f"  ✅ Token valid: Found profile for {profile.user.username}")
                except Profile.DoesNotExist:
                    print("  ❌ Token invalid: No profile found with this token")
    else:
        print("  ❌ No headers configured")

    print()

# Test with a sample blog post if available
blog_post = GeneratedBlogPost.objects.first()
if blog_post and settings.exists():
    print("=== Testing with sample blog post ===")
    setting = settings.first()

    print("Before placeholder replacement:")
    print(f"  Headers: {setting.header}")
    print(f"  Body: {setting.body}")

    processed_headers = replace_placeholders(setting.header, blog_post)
    processed_body = replace_placeholders(setting.body, blog_post)

    print()
    print("After placeholder replacement:")
    print(f"  Headers: {processed_headers}")
    print(f"  Body: {processed_body}")

    # Check for common issues
    if processed_headers == setting.header:
        print("  ℹ️  No placeholders were replaced in headers")
    if processed_body == setting.body:
        print("  ℹ️  No placeholders were replaced in body")

print("=== Configuration Check Complete ===")
