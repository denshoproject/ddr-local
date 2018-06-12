# http://docs.celeryproject.org/en/v4.2.0/django/first-steps-with-django.html

from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

PROJECT = 'ddrlocal'

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '%s.settings' % PROJECT)

app = Celery(PROJECT)

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
