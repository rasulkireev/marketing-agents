from django_q.tasks import async_task

from core.models import Project, ProjectPage
from core.tasks import schedule_project_page_analysis

project_ids_with_pages = ProjectPage.objects.values_list("project_id", flat=True).distinct()
projects_without_pages = Project.objects.exclude(id__in=project_ids_with_pages)

for project in projects_without_pages:
    if project.links:
        async_task(schedule_project_page_analysis, project.id)
