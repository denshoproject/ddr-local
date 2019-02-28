from datetime import datetime, timedelta
import os

from elasticsearch.exceptions import ConnectionError

from celery import task
from celery import Task
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from django.conf import settings

from webui import docstore
from webui import gitstatus
from webui.models import Collection, Entity, DDRFile
from webui.identifier import Identifier

from DDR import commands
from DDR import converters
from DDR import models
from DDR.ingest import addfile_logger

from .common import TASK_STATUSES, TASK_STATUSES_DISMISSABLE, TASK_STATUS_MESSAGES
from .common import DebugTask


# ----------------------------------------------------------------------

class FileAddDebugTask(Task):
    abstract = True
        
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        entity = args[2]
        log = addfile_logger(entity.identifier)
        log.not_ok('DDRTask.ON_FAILURE')
    
    def on_success(self, retval, task_id, args, kwargs):
        entity = args[2]
        log = addfile_logger(entity.identifier)
        log.ok('DDRTask.ON_SUCCESS')
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        entity = args[2]
        collection = entity.collection()
        log = addfile_logger(entity.identifier)
        log.ok('FileAddDebugTask.AFTER_RETURN')
        log.ok('task_id: %s' % task_id)
        log.ok('status: %s' % status)
        log.ok('retval: %s' % retval)
        log.ok('Unlocking %s' % entity.id)
        lockstatus = entity.unlock(task_id)
        if lockstatus == 'ok':
            log.ok('unlocked')
        else:
            log.not_ok(lockstatus)
        log.ok( 'END task_id %s\n' % task_id)
        collection.cache_delete()
        gitstatus.update(settings.MEDIA_BASE, collection.path)
        gitstatus.unlock(settings.MEDIA_BASE, 'entity_add_file')

@task(base=FileAddDebugTask, name='entity-add-file')
def add_file( git_name, git_mail, entity, src_path, role, data, agent='' ):
    """
    @param entity: Entity
    @param src_path: Absolute path to an uploadable file.
    @param role: Keyword of a file role.
    @param data: Dict containing form data.
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    @param agent: (optional) Name of software making the change.
    """
    gitstatus.lock(settings.MEDIA_BASE, 'entity_add_file')

    # TODO move this code to webui.models.Entity or .File
    file_,repo,log = entity.add_local_file(
        src_path, role, data,
        git_name, git_mail, agent
    )
    file_,repo,log = entity.add_file_commit(
        file_, repo, log,
        git_name, git_mail, agent
    )
    
    log.ok('Updating Elasticsearch')
    logger.debug('Updating Elasticsearch')
    if settings.DOCSTORE_ENABLED:
        try:
            result = file_.post_json()
            log.ok('| %s' % result)
        except ConnectionError:
            log.not_ok('Could not post to Elasticsearch.')
    
    return {
        'id': file_.id,
        'status': 'ok'
    }

@task(base=FileAddDebugTask, name='entity-add-external')
def add_external( git_name, git_mail, entity, data, agent='' ):
    """
    @param entity: Entity
    @param data: Dict containing form data.
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    @param agent: (optional) Name of software making the change.
    """
    gitstatus.lock(settings.MEDIA_BASE, 'entity_add_external')
    
    file_,repo,log = entity.add_external_file(
        data,
        git_name, git_mail, agent
    )
    file_,repo,log = entity.add_file_commit(
        file_, repo, log,
        git_name, git_mail, agent
    )
    
    log.ok('Updating Elasticsearch')
    logger.debug('Updating Elasticsearch')
    if settings.DOCSTORE_ENABLED:
        try:
            result = file_.post_json()
            log.ok('| %s' % result)
        except ConnectionError:
            log.not_ok('Could not post to Elasticsearch.')
    
    return {
        'id': file_.id,
        'status': 'ok'
    }

@task(base=FileAddDebugTask, name='entity-add-access')
def add_access( git_name, git_mail, entity, ddrfile, agent='' ):
    """
    @param entity: Entity
    @param ddrfile: DDRFile
    @param src_path: Absolute path to an uploadable file.
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    @param agent: (optional) Name of software making the change.
    """
    gitstatus.lock(settings.MEDIA_BASE, 'entity_add_access')
    
    file_,repo,log,op = entity.add_access(
        ddrfile, ddrfile.path_abs,
        git_name, git_mail, agent
    )
    if op and (op == 'pass'):
        log.ok('Things are okay as they are.  Leaving them alone.')
        return file_.__dict__
    file_,repo,log = entity.add_file_commit(
        file_, repo, log,
        git_name, git_mail, agent
    )
    
    log.ok('Updating Elasticsearch')
    logger.debug('Updating Elasticsearch')
    if settings.DOCSTORE_ENABLED:
        try:
            file_.post_json()
        except ConnectionError:
            log.not_ok('Could not post to Elasticsearch.')
    
    return {
        'id': file_.id,
        'status': 'ok'
    }


# ----------------------------------------------------------------------

def edit(request, collection, file_, form_data, git_name, git_mail):
    # start tasks
    
    result = file_edit.apply_async(
        (collection.path, file_.id, form_data, git_name, git_mail),
        countdown=2
    )
    
    # lock collection
    lockstatus = collection.lock(result.task_id)
    # add celery task_id to session
    celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
    celery_tasks[result.task_id] = {
        'task_id': result.task_id,
        'action': 'file-edit',
        'file_url': file_.absolute_url(),
        'file_id': file_.id,
        'start': converters.datetime_to_text(datetime.now(settings.TZ)),}
    request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks

class FileEditTask(Task):
    abstract = True
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        logger.debug('FileEditTask.after_return(%s, %s, %s, %s, %s)' % (status, retval, task_id, args, kwargs))
        collection_path = args[0]
        collection = Collection.from_identifier(Identifier(path=collection_path))
        lockstatus = collection.unlock(task_id)
        gitstatus.update(settings.MEDIA_BASE, collection_path)
        gitstatus.unlock(settings.MEDIA_BASE, 'file_edit')

@task(base=FileEditTask, name='file-edit')
def file_edit(collection_path, file_id, form_data, git_name, git_mail):
    """The time-consuming parts of file-edit.
    
    @param collection_path: str Absolute path to collection
    @param file_id: str
    @param form_data: dict
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    """
    logger.debug('tasks.files.edit(%s,%s,%s,%s)' % (git_name, git_mail, collection_path, file_id))
    fidentifier = Identifier(id=file_id)
    file_ = DDRFile.from_identifier(fidentifier)
    gitstatus.lock(settings.MEDIA_BASE, 'file_edit')
    
    exit,status,updated_files = file_.save(
        git_name, git_mail,
        form_data
    )
    
    gitstatus_update.apply_async(
        (collection_path,),
        countdown=2
    )
    return status,collection_path,file_id


# ----------------------------------------------------------------------

def delete(request, git_name, git_mail, collection, entity, file_, agent):
    # start tasks
    
    result = delete_file.apply_async(
        (git_name, git_mail, collection.path, entity.id, file_.basename, agent),
        countdown=2
    )
    
    # lock collection
    lockstatus = collection.lock(result.task_id)
    # add celery task_id to session
    celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
    celery_tasks[result.task_id] = {
        'task_id': result.task_id,
        'action': 'file-delete',
        'entity_url': entity.absolute_url(),
        'entity_id': entity.id,
        'filename': file_.basename,
        'file_url': file_.absolute_url(),
        'start': converters.datetime_to_text(datetime.now(settings.TZ)),}
    request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks

class DeleteFileTask(Task):
    abstract = True
        
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.debug('DeleteFileTask.on_failure(%s, %s, %s, %s)' % (exc, task_id, args, kwargs))
    
    def on_success(self, retval, task_id, args, kwargs):
        logger.debug('DeleteFileTask.on_success(%s, %s, %s, %s)' % (retval, task_id, args, kwargs))
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        logger.debug('DeleteFileTask.after_return(%s, %s, %s, %s, %s)' % (status, retval, task_id, args, kwargs))
        collection_path = args[2]
        collection = Collection.from_identifier(Identifier(path=collection_path))
        lockstatus = collection.unlock(task_id)
        gitstatus.update(settings.MEDIA_BASE, collection_path)
        gitstatus.unlock(settings.MEDIA_BASE, 'delete_file')

@task(base=DeleteFileTask, name='file-delete')
def delete_file( git_name, git_mail, collection_path, entity_id, file_basename, agent='' ):
    """
    @param collection_path: string
    @param entity_id: string
    @param file_basename: string
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    @param agent: (optional) Name of software making the change.
    """
    logger.debug('tasks.files.delete_file(%s,%s,%s,%s,%s,%s)' % (git_name, git_mail, collection_path, entity_id, file_basename, agent))
    
    gitstatus.lock(settings.MEDIA_BASE, 'delete_file')
    file_id = os.path.splitext(file_basename)[0]
    file_ = DDRFile.from_identifier(Identifier(file_id))

    # TODO move this code to webui.models.File.delete
    exit,status,rm_files,updated_files = file_.delete(
        git_name, git_mail, agent
    )
    logger.debug('delete from search index')
    if settings.DOCSTORE_ENABLED:
        ds = docstore.Docstore()
        try:
            ds.delete(file_.id)
        except ConnectionError:
            logger.error('Could not delete document from Elasticsearch.')
    
    return exit,status,collection_path,file_basename
