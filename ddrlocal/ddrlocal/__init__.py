# http://docs.celeryproject.org/en/v4.2.0/django/first-steps-with-django.html

from __future__ import absolute_import, unicode_literals

# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app as celery_app

__all__ = ('celery_app',)
