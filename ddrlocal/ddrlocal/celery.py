# reference: http://docs.celeryproject.org/en/latest/django/first-steps-with-django.html

from __future__ import absolute_import
import os

from celery import Celery

from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ddrlocal.settings')

app = Celery('ddrlocal')

app.config_from_object(settings)
# Using a string here means the worker will not have to
# pickle the object when using Windows.
#app.config_from_object('django.conf:settings')

# This tells Celery to autodiscover tasks.py in reusable Django apps.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
