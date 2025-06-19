from django.core.management.base import BaseCommand, CommandError
from django_q.tasks import async_task

from core.models import Project


class Command(BaseCommand):
    help = "Backfills analysis for all unanalyzed projects"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Force reanalysis of all projects")
        parser.add_argument("--project-ids", type=str, help="Comma-separated project IDs (e.g. '1,2,3')")

    def handle(self, *args, **options):
        projects = Project.objects.all()

        if project_ids := options.get("project_ids"):
            try:
                ids = [int(id.strip()) for id in project_ids.split(",")]
                projects = projects.filter(id__in=ids)
            except ValueError:
                raise CommandError("Invalid project IDs format")

        elif not options["force"]:
            projects = projects.filter(date_analyzed__isnull=True)

        if not (count := projects.count()):
            self.stdout.write(self.style.WARNING("No projects found"))
            return

        self.stdout.write(f"Queuing {count} projects for analysis...")

        for project in projects.iterator():
            async_task(project.analyze_content, group="backfill_project_analysis")

        self.stdout.write(self.style.SUCCESS(f"Queued {count} projects"))
