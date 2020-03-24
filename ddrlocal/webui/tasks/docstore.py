from datetime import datetime
import os

from celery import task
from celery import Task
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from django.conf import settings

from DDR import converters
from DDR import models


class ElasticsearchTask(Task):
    abstract = True
        
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.debug('ElasticsearchTask.on_failure(%s, %s, %s, %s)' % (exc, task_id, args, kwargs))
    
    def on_success(self, retval, task_id, args, kwargs):
        logger.debug('ElasticsearchTask.on_success(%s, %s, %s, %s)' % (retval, task_id, args, kwargs))
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        gitstatus.unlock(settings.MEDIA_BASE, 'reindex')
        logger.debug('ElasticsearchTask.after_return(%s, %s, %s, %s, %s)' % (status, retval, task_id, args, kwargs))

@task(base=ElasticsearchTask, name='search-reindex')
def reindex( index ):
    """
    @param index: Name of index to create or update
    """
    gitstatus.lock(settings.MEDIA_BASE, 'reindex')
    logger.debug('------------------------------------------------------------------------')
    logger.debug('webui.tasks.reindex(%s)' % index)
    statuses = []
    if not settings.DOCSTORE_ENABLED:
        raise Exception('Elasticsearch is not enabled. Please see your settings.')
    if not os.path.exists(settings.MEDIA_BASE):
        raise NameError('MEDIA_BASE does not exist - you need to remount!')
    logger.debug('webui.tasks.reindex(%s)' % index)
    logger.debug('DOCSTORE_HOSTS: %s' % settings.DOCSTORE_HOSTS)
    ds = docstore.Docstore(index=index)
    logger.debug('- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - ')
    logger.debug('deleting existing index: %s' % index)
    delete_status = ds.delete_index()
    logger.debug(delete_status)
    logger.debug('- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - ')
    logger.debug('creating new index: %s' % index)
    create_status = ds.create_index()
    logger.debug(create_status)
    logger.debug('- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - ')
    logger.debug('mappings: %s, %s' % (docstore.HARD_CODED_MAPPINGS_PATH, models.MODELS_DIR))
    mappings_status = ds.put_mappings(
        docstore.HARD_CODED_MAPPINGS_PATH, models.MODELS_DIR
    )
    logger.debug(mappings_status)
    logger.debug('- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - ')
    logger.debug('facets')
    facets_status = ds.put_facets()
    logger.debug(facets_status)
    logger.debug('- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - ')
    logger.debug('indexing/publishing')
    publish_status = ds.publish(
        path=settings.MEDIA_BASE,
        recursive=True, public=False
    )
    logger.debug(publish_status)
    return statuses

def reindex_and_notify( index ):
    """Drop existing index and build another from scratch; hand off to Celery.
    This function is intended for use in a view.
    """
    result = reindex(index).apply_async(
        countdown=2
    )
    celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
    task = {
        'task_id': result.task_id,
        'action': 'search-reindex',
        'index': index,
        'start': converters.datetime_to_text(datetime.now(settings.TZ)),
    }
    celery_tasks[result.task_id] = task
    request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks
