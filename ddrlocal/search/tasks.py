from celery import task
from celery import Task
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

import search


class DebugTask(Task):
    abstract = True

@task(base=DebugTask, name='search-reindex')
def reindex():
    """
    """
    search.index('/var/www/media/base')
    return 0
