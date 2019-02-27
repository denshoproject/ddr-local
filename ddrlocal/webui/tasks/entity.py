from datetime import datetime, timedelta
import os

from elasticsearch.exceptions import ConnectionError

from celery import task
from celery import Task
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from django.conf import settings
from django.contrib import messages

from webui import docstore
from webui import gitstatus
from webui.models import Collection, Entity, DDRFile
from webui.identifier import Identifier

from DDR import commands
from DDR import converters

from .common import TASK_STATUSES, TASK_STATUSES_DISMISSABLE, TASK_STATUS_MESSAGES
from .common import DebugTask


# ----------------------------------------------------------------------

def collection_entity_edit(request, collection, entity, form_data, git_name, git_mail, agent):
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
        'action': 'webui-entity-edit',
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

@task(base=EntityEditTask, name='webui-entity-edit')
def entity_edit(collection_path, entity_id, form_data, git_name, git_mail, agent=''):
    """The time-consuming parts of entity-edit.
    
    @param collection_path: str Absolute path to collection
    @param entity_id: str
    @param form_data: dict
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    @param agent: (optional) Name of software making the change.
    """
    logger.debug('collection_entity_edit(%s,%s,%s,%s,%s)' % (
        git_name, git_mail, collection_path, entity_id, agent))
    collection = Collection.from_identifier(Identifier(path=collection_path))
    entity = Entity.from_identifier(Identifier(id=entity_id))
    gitstatus.lock(settings.MEDIA_BASE, 'entity_edit')
    
    exit,status,updated_files = entity.save(
        git_name, git_mail,
        collection,
        form_data
    )
    
    gitstatus_update.apply_async(
        (collection.path,),
        countdown=2
    )
    return status,collection_path,entity_id

# ------------------------------------------------------------------------

def collection_delete_entity(request, git_name, git_mail, collection, entity, agent):
    # start tasks
    
    result = delete_entity.apply_async(
        (git_name, git_mail, collection.path, entity.id, agent),
        countdown=2
    )
    
    # lock collection
    lockstatus = collection.lock(result.task_id)
    # add celery task_id to session
    celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
    celery_tasks[result.task_id] = {
        'task_id': result.task_id,
        'action': 'webui-entity-delete',
        'collection_url': collection.absolute_url(),
        'collection_id': collection.id,
        'entity_url': entity.absolute_url(),
        'entity_id': entity.id,
        'start': converters.datetime_to_text(datetime.now(settings.TZ)),}
    request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks

class DeleteEntityTask(Task):
    abstract = True
        
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.debug('DeleteEntityTask.on_failure(%s, %s, %s, %s)' % (exc, task_id, args, kwargs))
    
    def on_success(self, retval, task_id, args, kwargs):
        logger.debug('DeleteEntityTask.on_success(%s, %s, %s, %s)' % (retval, task_id, args, kwargs))
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        logger.debug('DeleteEntityTask.after_return(%s, %s, %s, %s, %s)' % (status, retval, task_id, args, kwargs))
        collection_path = args[2]
        collection = Collection.from_identifier(Identifier(path=collection_path))
        lockstatus = collection.unlock(task_id)
        gitstatus.update(settings.MEDIA_BASE, collection_path)
        gitstatus.unlock(settings.MEDIA_BASE, 'delete_entity')

@task(base=DeleteEntityTask, name='webui-entity-delete')
def delete_entity( git_name, git_mail, collection_path, entity_id, agent='' ):
    """
    @param collection_path: string
    @param entity_id: string
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    @param agent: (optional) Name of software making the change.
    """
    gitstatus.lock(settings.MEDIA_BASE, 'delete_entity')
    logger.debug('collection_delete_entity(%s,%s,%s,%s,%s)' % (git_name, git_mail, collection_path, entity_id, agent))
    # remove the entity
    collection = Collection.from_identifier(Identifier(collection_path))
    entity = Entity.from_identifier(Identifier(entity_id))

    # TODO move this code to webui.models.Entity.delete
    status,message = commands.entity_destroy(
        git_name, git_mail,
        collection, entity,
        agent
    )
    logger.debug('Updating Elasticsearch')
    if settings.DOCSTORE_ENABLED:
        ds = docstore.Docstore()
        try:
            ds.delete(entity_id)
        except ConnectionError:
            logger.error('Could not delete document from Elasticsearch.')
    
    return status,message,collection_path,entity_id

# ----------------------------------------------------------------------

def entity_reload_files(request, collection, entity, git_name, git_mail, agent):
    # start tasks
    
    result = reload_files.apply_async(
        (collection.path, entity.id, git_name, git_mail, agent),
        countdown=2
    )
    
    # lock collection
    lockstatus = entity.lock(result.task_id)
    # add celery task_id to session
    celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
    celery_tasks[result.task_id] = {
        'task_id': result.task_id,
        'action': 'webui-entity-reload-files',
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
        lockstatus = entity.unlock(task_id)
        gitstatus.update(settings.MEDIA_BASE, collection_path)
        gitstatus.unlock(settings.MEDIA_BASE, 'reload_files')

@task(base=EntityReloadTask, name='webui-entity-reload-files')
def reload_files(collection_path, entity_id, git_name, git_mail, agent=''):
    """Regenerate entity.json's list of child files.
    
    @param collection_path: string
    @param entity_id: string
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    @param agent: (optional) Name of software making the change.
    """
    logger.debug('reload_files(%s,%s,%s,%s,%s)' % (collection_path, entity_id, git_name, git_mail, agent))
    gitstatus.lock(settings.MEDIA_BASE, 'reload_files')
    entity = Entity.from_identifier(Identifier(entity_id))
    collection = Collection.from_identifier(Identifier(path=collection_path))
    
    exit,status,updated_files = entity.save(
        git_name, git_mail,
        collection,
        {}
    )

    return status,collection_path,entity_id
