from datetime import datetime

from celery import task
from celery import Task
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from django.conf import settings

import search


class DebugTask(Task):
    abstract = True

@task(base=DebugTask, name='search-reindex')
def reindex():
    """
    """
    search.index('ddr', '/var/www/media/base')
    return 0

def reindex_and_notify( request ):
    """Drop existing index and build another from scratch; hand off to Celery.
    This function is intended for use in a view.
    """
    result = reindex.apply_async( (), countdown=2)
    celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
    task = {'task_id': result.task_id,
            'action': 'search-reindex',
            'start': datetime.now().strftime(settings.TIMESTAMP_FORMAT),}
    celery_tasks[result.task_id] = task
    request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks
