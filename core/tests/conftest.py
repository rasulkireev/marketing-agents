from django.conf import settings
from django.core.management import call_command

def pytest_configure(config):
    settings.STORAGES['staticfiles']['BACKEND'] = 'django.contrib.staticfiles.storage.StaticFilesStorage'
