from django_q.tasks import async_task

from core.models import Project

unscraped_projects = Project.objects.filter(date_scraped__isnull=True)

for project in unscraped_projects:
    async_task(project.get_page_content())
