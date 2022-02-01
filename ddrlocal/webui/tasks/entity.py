from datetime import datetime

from elasticsearch.exceptions import ConnectionError, RequestError

from celery import shared_task
from celery import Task
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from django.conf import settings

from DDR import converters

from webui import docstore
from webui import gitstatus
from webui.models import Collection, Entity
from webui.identifier import Identifier
from webui.tasks import dvcs as dvcs_tasks


# ----------------------------------------------------------------------

def edit(request, collection, entity, form_data, git_name, git_mail, agent):
    # start tasks
    
    result = entity_edit.apply_async(
        (collection.path, entity.id, form_data, git_name, git_mail, agent),
        countdown=2
    )
    
    # lock collection
    lockstatus = collection.lock(result.task_id)
    # add celery task_id to session
    celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
    celery_tasks[result.task_id] = {
        'task_id': result.task_id,
        'action': 'entity-edit',
        'collection_url': collection.absolute_url(),
        'collection_id': collection.id,
        'entity_url': entity.absolute_url(),
        'entity_id': entity.id,
        'start': converters.datetime_to_text(datetime.now(settings.TZ)),}
    request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks

class EntityEditTask(Task):
    abstract = True
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.debug('EntityEditTask.on_failure(%s, %s, %s, %s)' % (exc, task_id, args, kwargs))
    
    def on_success(self, retval, task_id, args, kwargs):
        logger.debug('EntityEditTask.on_success(%s, %s, %s, %s)' % (retval, task_id, args, kwargs))
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        logger.debug('EntityEditTask.after_return(%s, %s, %s, %s, %s)' % (status, retval, task_id, args, kwargs))
        collection_path = args[0]
        collection = Collection.from_identifier(Identifier(path=collection_path))
        lockstatus = collection.unlock(task_id)
        gitstatus.update(settings.MEDIA_BASE, collection_path)
        gitstatus.unlock(settings.MEDIA_BASE, 'entity_edit')

@shared_task(base=EntityEditTask, name='entity-edit')
def entity_edit(collection_path, entity_id, form_data, git_name, git_mail, agent=''):
    """The time-consuming parts of entity-edit.
    
    @param collection_path: str Absolute path to collection
    @param entity_id: str
    @param form_data: dict
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    @param agent: (optional) Name of software making the change.
    """
    logger.debug('tasks.entity.entity_edit(%s,%s,%s,%s,%s)' % (
        git_name, git_mail, collection_path, entity_id, agent))
    collection = Collection.from_identifier(Identifier(path=collection_path))
    entity = Entity.from_identifier(Identifier(id=entity_id))
    gitstatus.lock(settings.MEDIA_BASE, 'entity_edit')
    
    try:
        exit,status,updated_files = entity.save(
            git_name, git_mail, collection, form_data
        )
    except ConnectionError as err:
        logger.error("ConnectionError: {0}".format(err))
        exit = 1; status = {'error': err}
    except RequestError as err:
        logger.error("RequestError: {0}".format(err))
        exit = 1; status = {'error': err}
    except FileNotFoundError as err:
        # don't crash if file absent from Internet Archive
        logger.error("FileNotFoundError: {0}".format(err))
        exit = 1; status = {'error': str(err)}
    
    dvcs_tasks.gitstatus_update.apply_async(
        (collection.path,),
        countdown=2
    )
    return status,collection_path,entity_id

# ------------------------------------------------------------------------

def delete(request, collection, entity, git_name, git_mail, agent):
    # start tasks
    result = entity_delete.apply_async(
        (collection.path, entity.id, git_name, git_mail, agent),
        countdown=2
    )
    # lock collection
    lockstatus = collection.lock(result.task_id)
    # add celery task_id to session
    celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
    celery_tasks[result.task_id] = {
        'task_id': result.task_id,
        'action': 'entity-delete',
        'collection_url': collection.absolute_url(),
        'collection_id': collection.id,
        'entity_url': entity.absolute_url(),
        'entity_id': entity.id,
        'start': converters.datetime_to_text(datetime.now(settings.TZ)),}
    request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks

class DeleteEntityTask(Task):
    abstract = True
        
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.debug('DeleteEntityTask.on_failure(%s, %s, %s, %s)' % (
            exc, task_id, args, kwargs
        ))
    
    def on_success(self, retval, task_id, args, kwargs):
        logger.debug('DeleteEntityTask.on_success(%s, %s, %s, %s)' % (
            retval, task_id, args, kwargs
        ))
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        logger.debug('DeleteEntityTask.after_return(%s, %s, %s, %s, %s)' % (
            status, retval, task_id, args, kwargs
        ))
        collection_path = args[0]
        collection = Collection.from_identifier(Identifier(path=collection_path))
        lockstatus = collection.unlock(task_id)
        gitstatus.update(settings.MEDIA_BASE, collection_path)
        gitstatus.unlock(settings.MEDIA_BASE, 'entity_delete')

@shared_task(base=DeleteEntityTask, name='entity-delete')
def entity_delete(collection_path, entity_id, git_name, git_mail, agent):
    """The time-consuming parts of entity-delete.
    
    @param collection_path: str Absolute path to collection
    @param entity_id: str
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    @param agent: (optional) Name of software making the change.
    """
    logger.debug('tasks.entity.delete(%s,%s,%s,%s,%s)' % (
        collection_path, entity_id, git_name, git_mail, agent
    ))
    collection = Collection.from_identifier(Identifier(path=collection_path))
    entity = Entity.from_identifier(Identifier(id=entity_id))
    #gitstatus.lock(settings.MEDIA_BASE, 'entity_delete')
    
    try:
        status,message = entity.delete(
            git_name, git_mail, agent, commit=True
        )
    except ConnectionError as err:
        logger.error("ConnectionError: {0}".format(err))
        exit = 1; status = {'error': err}
    except RequestError as err:
        logger.error("RequestError: {0}".format(err))
        exit = 1; status = {'error': err}
    
    dvcs_tasks.gitstatus_update.apply_async(
        (collection.path,),
        countdown=2
    )
    
    logger.debug('Updating Elasticsearch')
    if settings.DOCSTORE_ENABLED:
        ds = docstore.Docstore()
        try:
            ds.delete(entity.id)
        except ConnectionError:
            logger.error('Could not delete document from Elasticsearch.')
    return status,message,collection.path_abs,entity.id

# ----------------------------------------------------------------------

def entity_reload_files(request, collection, entity, git_name, git_mail, agent):
    # start tasks
    
    result = reload_files.apply_async(
        (collection.path, entity.id, git_name, git_mail, agent),
        countdown=2
    )
    
    # lock collection
    lockstatus = collection.lock(result.task_id)
    # add celery task_id to session
    celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
    celery_tasks[result.task_id] = {
        'task_id': result.task_id,
        'action': 'entity-reload-files',
        'entity_url': entity.absolute_url(),
        'entity_id': entity.id,
        'start': converters.datetime_to_text(datetime.now(settings.TZ)),}
    request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks

class EntityReloadTask(Task):
    abstract = True
        
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.debug('EntityReloadTask.on_failure(%s, %s, %s, %s)' % (exc, task_id, args, kwargs))
    
    def on_success(self, retval, task_id, args, kwargs):
        logger.debug('EntityReloadTask.on_success(%s, %s, %s, %s)' % (retval, task_id, args, kwargs))
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        logger.debug('EntityReloadTask.after_return(%s, %s, %s, %s, %s)' % (status, retval, task_id, args, kwargs))
        collection_path = args[0]
        collection = Collection.from_identifier(Identifier(path=collection_path))
        entity_id = args[1]
        entity = Entity.from_identifier(Identifier(id=entity_id))
        lockstatus = collection.unlock(task_id)
        gitstatus.update(settings.MEDIA_BASE, collection_path)
        gitstatus.unlock(settings.MEDIA_BASE, 'reload_files')

@shared_task(base=EntityReloadTask, name='entity-reload-files')
def reload_files(collection_path, entity_id, git_name, git_mail, agent=''):
    """Regenerate entity.json's list of child files.
    
    @param collection_path: string
    @param entity_id: string
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    @param agent: (optional) Name of software making the change.
    """
    logger.debug('tasks.entity.reload_files(%s,%s,%s,%s,%s)' % (collection_path, entity_id, git_name, git_mail, agent))
    gitstatus.lock(settings.MEDIA_BASE, 'reload_files')
    entity = Entity.from_identifier(Identifier(entity_id))
    collection = Collection.from_identifier(Identifier(path=collection_path))
    
    exit,status,updated_files = entity.save(
        git_name, git_mail,
        collection,
        {}
    )

    return status,collection_path,entity_id
