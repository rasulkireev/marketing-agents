from django_q.tasks import async_task

from core.models import Project

unanalyzed_projects = Project.objects.filter(date_analyzed__isnull=True)

for project in unanalyzed_projects:
    async_task(project.analyze_content)
