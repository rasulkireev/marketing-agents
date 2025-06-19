from django.core.management.base import BaseCommand, CommandError
from django_q.tasks import async_task

from core.models import Project, ProjectPage
from core.tasks import schedule_project_page_analysis


class Command(BaseCommand):
    help = "Backfills page analysis for projects without analyzed pages"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Force page analysis for all projects")
        parser.add_argument("--project-ids", type=str, help="Comma-separated project IDs (e.g. '1,2,3')")

    def handle(self, *args, **options):
        # Get base queryset of all projects
        projects = Project.objects.all()

        # Filter by specific project IDs if provided
        if project_ids := options.get("project_ids"):
            try:
                ids = [int(id.strip()) for id in project_ids.split(",")]
                projects = projects.filter(id__in=ids)
            except ValueError:
                raise CommandError("Invalid project IDs format")

        # If not forcing all projects, only get those without pages
        if not options["force"]:
            project_ids_with_pages = ProjectPage.objects.values_list("project_id", flat=True).distinct()
            projects = projects.exclude(id__in=project_ids_with_pages)

        # Further filter to only projects that have links
        projects = projects.exclude(links__isnull=True).exclude(links=[])

        if not (count := projects.count()):
            self.stdout.write(self.style.WARNING("No eligible projects found"))
            return

        self.stdout.write(f"Queuing {count} projects for page analysis...")

        for project in projects.iterator():
            async_task(schedule_project_page_analysis, project.id, group="backfill_project_pages")

        self.stdout.write(self.style.SUCCESS(f"Queued {count} projects for page analysis"))
