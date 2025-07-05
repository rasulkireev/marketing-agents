from django.core.management.base import BaseCommand
from django.utils import timezone

from core.tasks import check_and_schedule_blog_posts


class Command(BaseCommand):
    help = "Check AutoSubmissionSettings and schedule blog posts for projects that need them"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be scheduled without actually scheduling",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE: No actual scheduling will occur")
            )
            # For dry run, we could create a modified version of the function
            # that doesn't actually schedule tasks but shows what would be scheduled
            return
        
        self.stdout.write(f"Starting blog post scheduling check at {timezone.now()}")
        
        try:
            result = check_and_schedule_blog_posts()
            self.stdout.write(
                self.style.SUCCESS(f"Blog post scheduling completed: {result}")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error during blog post scheduling: {str(e)}")
            )
            raise e