from django.core.management.base import BaseCommand, CommandError
from django_q.tasks import async_task

from core.models import Project
from core.tasks import schedule_project_competitor_analysis


class Command(BaseCommand):
    help = "Backfills competitor analysis for projects without analyzed competitors"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Force competitor analysis for all projects")
        parser.add_argument("--project-ids", type=str, help="Comma-separated project IDs (e.g. '1,2,3')")

    def handle(self, *args, **options):
        projects = Project.objects.all()

        if project_ids := options.get("project_ids"):
            try:
                ids = [int(id.strip()) for id in project_ids.split(",")]
                projects = projects.filter(id__in=ids)
            except ValueError:
                raise CommandError("Invalid project IDs format")

        if not options["force"]:
            projects = Project.objects.filter(competitors_list="")

        if not (count := projects.count()):
            self.stdout.write(self.style.WARNING("No eligible projects found"))
            return

        self.stdout.write(f"Queuing {count} projects for competitor analysis...")

        for project in projects.iterator():
            async_task(schedule_project_competitor_analysis, project.id, group="backfill_project_competitors")

        self.stdout.write(self.style.SUCCESS(f"Queued {count} projects for competitor analysis"))
