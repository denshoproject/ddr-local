from __future__ import absolute_import
import os

# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app as celery_app

VERSION = '0.9.3-beta'
