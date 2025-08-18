from core.models import AutoSubmissionSetting

settings = AutoSubmissionSetting.objects.all()
for setting in settings:
    print(f"Setting ID: {setting.id}")
    print(f"Project: {setting.project.name}")
    print(f"Endpoint URL: {setting.endpoint_url}")
    print(f"Headers: {setting.header}")
    print(f"Body: {setting.body}")
    print("-" * 50)
