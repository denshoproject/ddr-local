from datetime import datetime, timedelta
import json
import os

from elasticsearch.exceptions import ConnectionError

from celery import task
from celery import Task
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from celery import states
from celery.result import AsyncResult
from celery.utils.encoding import safe_repr
from celery.utils import get_full_cls_name

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.urlresolvers import reverse

from webui import docstore
from webui import GITOLITE_INFO_CACHE_KEY
from webui import gitolite
from webui import gitstatus
from webui.models import Collection, Entity, DDRFile
from webui.identifier import Identifier

from DDR import batch
from DDR import commands
from DDR import converters
from DDR import dvcs
from DDR import models
from DDR import signatures
from DDR import util
from DDR.ingest import addfile_logger


TASK_STATUSES = ['STARTED', 'PENDING', 'SUCCESS', 'FAILURE', 'RETRY', 'REVOKED',]
TASK_STATUSES_DISMISSABLE = ['STARTED', 'SUCCESS', 'FAILURE', 'RETRY', 'REVOKED',]

# Background task status messages.
# IMPORTANT: These are templates.  Arguments (words in {parentheses}) MUST match keys in the task dict. 
# See "Accessing arguments by name" section on http://docs.python.org/2.7/library/string.html#format-examples
TASK_STATUS_MESSAGES = {
    'webui-file-new-master': {
        #'STARTED': '',
        'PENDING': 'Uploading <b>{filename}</b> to <a href="{entity_url}">{entity_id}</a>.',
        'SUCCESS': 'Uploaded <a href="{file_url}">{filename}</a> to <a href="{entity_url}">{entity_id}</a>.',
        'FAILURE': 'Could not upload <b>{filename}</b> to <a href="{entity_url}">{entity_id}</a>.<br/>{result}',
        #'RETRY': '',
        #'REVOKED': '',
        },
    'webui-file-new-mezzanine': {
        #'STARTED': '',
        'PENDING': 'Uploading <b>{filename}</b> to <a href="{entity_url}">{entity_id}</a>.',
        'SUCCESS': 'Uploaded <a href="{file_url}">{filename}</a> to <a href="{entity_url}">{entity_id}</a>.',
        'FAILURE': 'Could not upload <b>{filename}</b> to <a href="{entity_url}">{entity_id}</a>.<br/>{result}',
        #'RETRY': '',
        #'REVOKED': '',
        },
    'webui-file-new-access': {
        #'STARTED': '',
        'PENDING': 'Generating new access file for <b>{filename}</b> (<a href="{entity_url}">{entity_id}</a>).',
        'SUCCESS': 'Generated new access file for <a href="{file_url}">{filename}</a> (<a href="{entity_url}">{entity_id}</a>).',
        'FAILURE': 'Could not generate new access file for <a href="{file_url}">{filename}</a> (<a href="{entity_url}">{entity_id}</a>).',
        #'RETRY': '',
        #'REVOKED': '',
        },
    'webui-collection-sync': {
        #'STARTED': '',
        'PENDING': 'Syncing <b><a href="{collection_url}">{collection_id}</a></b> with the workbench server.',
        'SUCCESS': 'Synced <b><a href="{collection_url}">{collection_id}</a></b> with the workbench server.',
        'FAILURE': 'Could not sync <b><a href="{collection_url}">{collection_id}</a></b> with the workbench server.',
        #'RETRY': '',
        #'REVOKED': '',
        },
    'webui-collection-signatures': {
        #'STARTED': '',
        'PENDING': 'Choosing signatures for <b><a href="{collection_url}">{collection_id}</a></b>.',
        'SUCCESS': 'Signatures chosen for <b><a href="{collection_url}">{collection_id}</a></b>.',
        'FAILURE': 'Could not choose signatures for <b><a href="{collection_url}">{collection_id}</a></b>.',
        #'RETRY': '',
        #'REVOKED': '',
        },
    'webui-search-reindex': {
        #'STARTED': '',
        'PENDING': 'Recreating search index <b>{index}</b>.',
        'SUCCESS': 'Reindexing <b>{index}</b> completed.',
        'FAILURE': 'Reindexing <b>{index}</b> failed!',
        #'RETRY': '',
        #'REVOKED': '',
        },
}



class DebugTask(Task):
    abstract = True


class ElasticsearchTask(Task):
    abstract = True
        
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.debug('ElasticsearchTask.on_failure(%s, %s, %s, %s)' % (exc, task_id, args, kwargs))
    
    def on_success(self, retval, task_id, args, kwargs):
        logger.debug('ElasticsearchTask.on_success(%s, %s, %s, %s)' % (retval, task_id, args, kwargs))
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        gitstatus.unlock(settings.MEDIA_BASE, 'reindex')
        logger.debug('ElasticsearchTask.after_return(%s, %s, %s, %s, %s)' % (status, retval, task_id, args, kwargs))

@task(base=ElasticsearchTask, name='webui-search-reindex')
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
        'action': 'webui-search-reindex',
        'index': index,
        'start': converters.datetime_to_text(datetime.now(settings.TZ)),
    }
    celery_tasks[result.task_id] = task
    request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks



# ----------------------------------------------------------------------

@task(base=DebugTask, name='webui.tasks.gitolite_info_refresh')
def gitolite_info_refresh():
    """
    Check the cached value of DDR.dvcs.gitolite_info().
    If it is stale (e.g. timestamp is older than cutoff)
    then hit the Gitolite server for an update and re-cache.
    """
    return gitolite.refresh()



# ----------------------------------------------------------------------

class GitStatusTask(Task):
    abstract = True
        
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        pass
    
    def on_success(self, retval, task_id, args, kwargs):
        pass
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        logger.debug('GitStatusTask.after_return(%s, %s, %s, %s, %s, %s)' % (status, retval, task_id, args, kwargs, einfo))
        gitstatus.log('GitStatusTask.after_return(%s, %s, %s, %s, %s, %s)' % (status, retval, task_id, args, kwargs, einfo))

@task(base=GitStatusTask, name='webui.tasks.gitstatus_update')
def gitstatus_update( collection_path ):
    if not os.path.exists(settings.MEDIA_BASE):
        raise Exception('base_dir does not exist. No Store mounted?: %s' % settings.MEDIA_BASE)
    if not os.path.exists(gitstatus.queue_path(settings.MEDIA_BASE)):
        queue = gitstatus.queue_generate(
            settings.MEDIA_BASE,
            gitolite.get_repos_orgs()
        )
        gitstatus.queue_write(settings.MEDIA_BASE, queue)
    return gitstatus.update(settings.MEDIA_BASE, collection_path)

@task(base=GitStatusTask, name='webui.tasks.gitstatus_update_store')
def gitstatus_update_store():
    if not os.path.exists(settings.MEDIA_BASE):
        raise Exception('base_dir does not exist. No Store mounted?: %s' % settings.MEDIA_BASE)
    if not os.path.exists(gitstatus.queue_path(settings.MEDIA_BASE)):
        queue = gitstatus.queue_generate(
            settings.MEDIA_BASE,
            gitolite.get_repos_orgs()
        )
        gitstatus.queue_write(settings.MEDIA_BASE, queue)
    return gitstatus.update_store(
        base_dir=settings.MEDIA_BASE,
        delta=60,
        minimum=settings.GITSTATUS_INTERVAL,
    )



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
def entity_add_file( git_name, git_mail, entity, src_path, role, data, agent='' ):
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
    
    file_,repo,log = entity.add_local_file(
        src_path, role, data,
        git_name, git_mail, agent
    )
    file_,repo,log = entity.add_file_commit(
        file_, repo, log,
        git_name, git_mail, agent
    )
    
    log.ok('Updating Elasticsearch')
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
def entity_add_external( git_name, git_mail, entity, data, agent='' ):
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
def entity_add_access( git_name, git_mail, entity, ddrfile, agent='' ):
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

TASK_STATUS_MESSAGES['webui-collection-edit'] = {
    #'STARTED': '',
    'PENDING': 'Saving changes to collection <b><a href="{collection_url}">{collection_id}</a></b>...',
    'SUCCESS': 'Saved changes to collection <b><a href="{collection_url}">{collection_id}</a></b>.',
    'FAILURE': 'Could not save changes to collection <b><a href="{collection_url}">{collection_id}</a></b>.',
    #'RETRY': '',
    #'REVOKED': '',
}

def collection_edit(request, collection, cleaned_data, git_name, git_mail):
    # start tasks
    
    result = collection_save.apply_async(
        (collection.path, cleaned_data, git_name, git_mail),
        countdown=2
    )
    
    # lock collection
    lockstatus = collection.lock(result.task_id)
    # add celery task_id to session
    celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
    celery_tasks[result.task_id] = {
        'task_id': result.task_id,
        'action': 'webui-collection-edit',
        'collection_url': collection.absolute_url(),
        'collection_id': collection.id,
        'start': converters.datetime_to_text(datetime.now(settings.TZ)),}
    request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks

class CollectionEditTask(Task):
    abstract = True
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        logger.debug('CollectionEditTask.after_return(%s, %s, %s, %s, %s)' % (status, retval, task_id, args, kwargs))
        collection_path = args[0]
        collection = Collection.from_identifier(Identifier(path=collection_path))
        lockstatus = collection.unlock(task_id)
        gitstatus.update(settings.MEDIA_BASE, collection_path)
        gitstatus.unlock(settings.MEDIA_BASE, 'collection_edit')

@task(base=CollectionEditTask, name='webui-collection-edit')
def collection_save(collection_path, cleaned_data, git_name, git_mail):
    """The time-consuming parts of collection-edit.
    
    @param collection_path: str Absolute path to collection
    @param cleaned_data: dict form.cleaned_data
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    """
    logger.debug('collection_save(%s,%s,%s)' % (
        git_name, git_mail, collection_path))
    
    collection = Collection.from_identifier(Identifier(path=collection_path))
    gitstatus.lock(settings.MEDIA_BASE, 'collection_edit')
    
    exit,status,updated_files = collection.save(
        git_name, git_mail,
        cleaned_data
    )
    
    gitstatus_update.apply_async(
        (collection_path,),
        countdown=2
    )
    
    return status,collection_path

# ----------------------------------------------------------------------

TASK_STATUS_MESSAGES['webui-file-edit'] = {
    #'STARTED': '',
    'PENDING': 'Saving changes to file <b><a href="{file_url}">{file_id}</a></b>...',
    'SUCCESS': 'Saved changes to file <b><a href="{file_url}">{file_id}</a></b>.',
    'FAILURE': 'Could not save changes to file <b><a href="{file_url}">{file_id}</a></b>.',
    #'RETRY': '',
    #'REVOKED': '',
}

def entity_file_edit(request, collection, file_, form_data, git_name, git_mail):
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
        'action': 'webui-file-edit',
        'file_url': file_.absolute_url(),
        'file_id': file_.id,
        'start': converters.datetime_to_text(datetime.now(settings.TZ)),}
    request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks

# ----------------------------------------------------------------------

class FileEditTask(Task):
    abstract = True
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        logger.debug('FileEditTask.after_return(%s, %s, %s, %s, %s)' % (status, retval, task_id, args, kwargs))
        collection_path = args[0]
        collection = Collection.from_identifier(Identifier(path=collection_path))
        lockstatus = collection.unlock(task_id)
        gitstatus.update(settings.MEDIA_BASE, collection_path)
        gitstatus.unlock(settings.MEDIA_BASE, 'file_edit')

@task(base=FileEditTask, name='webui-file-edit')
def file_edit(collection_path, file_id, form_data, git_name, git_mail):
    """The time-consuming parts of file-edit.
    
    @param collection_path: str Absolute path to collection
    @param file_id: str
    @param form_data: dict
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    """
    logger.debug('file_edit(%s,%s,%s,%s)' % (git_name, git_mail, collection_path, file_id))
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

TASK_STATUS_MESSAGES['webui-entity-edit'] = {
    #'STARTED': '',
    'PENDING': 'Saving changes to object <b><a href="{entity_url}">{entity_id}</a></b>...',
    'SUCCESS': 'Saved changes to object <b><a href="{entity_url}">{entity_id}</a></b>.',
    'FAILURE': 'Could not save changes to object <b><a href="{entity_url}">{entity_id}</a></b>.',
    #'RETRY': '',
    #'REVOKED': '',
}

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

TASK_STATUS_MESSAGES['webui-entity-delete'] = {
    #'STARTED': '',
    'PENDING': 'Deleting object <b>{entity_id}</b> from <a href="{collection_url}">{collection_id}</a>.',
    'SUCCESS': 'Deleted object <b>{entity_id}</b> from <a href="{collection_url}">{collection_id}</a>.',
    'FAILURE': 'Could not delete object <a href="{entity_url}">{entity_id}</a> from <a href="{collection_url}">{collection_id}</a>.',
    #'RETRY': '',
    #'REVOKED': '',
}

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
    
    status,message = commands.entity_destroy(
        git_name, git_mail,
        collection, entity,
        agent
    )
    log.ok('Updating Elasticsearch')
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

# ----------------------------------------------------------------------

TASK_STATUS_MESSAGES['webui-file-delete'] = {
    #'STARTED': '',
    'PENDING': 'Deleting file <b>{filename}</b> from <a href="{entity_url}">{entity_id}</a>.',
    'SUCCESS': 'Deleted file <b>{filename}</b> from <a href="{entity_url}">{entity_id}</a>.',
    'FAILURE': 'Could not delete file <a href="{file_url}">{filename}</a> from <a href="{entity_url}">{entity_id}</a>.',
    #'RETRY': '',
    #'REVOKED': '',
}

def entity_delete_file(request, git_name, git_mail, collection, entity, file_, agent):
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
        'action': 'webui-file-delete',
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

@task(base=DeleteFileTask, name='webui-file-delete')
def delete_file( git_name, git_mail, collection_path, entity_id, file_basename, agent='' ):
    """
    @param collection_path: string
    @param entity_id: string
    @param file_basename: string
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    @param agent: (optional) Name of software making the change.
    """
    logger.debug('delete_file(%s,%s,%s,%s,%s,%s)' % (git_name, git_mail, collection_path, entity_id, file_basename, agent))
    
    gitstatus.lock(settings.MEDIA_BASE, 'delete_file')
    file_id = os.path.splitext(file_basename)[0]
    file_ = DDRFile.from_identifier(Identifier(file_id))

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

# ----------------------------------------------------------------------

class CollectionSyncDebugTask(Task):
    abstract = True
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        pass
    
    def on_success(self, retval, task_id, args, kwargs):
        pass
    
    def after_return(self, status, retval, task_id, args, kwargs, cinfo):
        collection_path = args[2]
        collection = Collection.from_identifier(Identifier(path=collection_path))
        # NOTE: collection is locked immediately after collection_sync task
        #       starts in webui.views.collections.sync
        collection.unlock(task_id)
        collection.cache_delete()
        gitstatus.update(settings.MEDIA_BASE, collection_path)
        gitstatus.unlock(settings.MEDIA_BASE, 'collection_sync')

@task(base=CollectionSyncDebugTask, name='collection-sync')
def collection_sync( git_name, git_mail, collection_path ):
    """Synchronizes collection repo with workbench server.
    
    @param src_path: Absolute path to collection repo.
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    @return collection_path: Absolute path to collection.
    """
    gitstatus.lock(settings.MEDIA_BASE, 'collection_sync')
    collection = Collection.from_identifier(Identifier(path=collection_path))
    
    exit,status = commands.sync(
        git_name, git_mail,
        collection
    )
    log.ok('Updating Elasticsearch')
    if settings.DOCSTORE_ENABLED:
        collection = Collection.from_identifier(Identifier(path=collection_path))
        try:
            collection.post_json()
        except ConnectionError:
            logger.error('Could not update search index')
    
    return collection_path


# ----------------------------------------------------------------------

class CollectionSignaturesDebugTask(Task):
    abstract = True
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        pass
    
    def on_success(self, retval, task_id, args, kwargs):
        pass
    
    def after_return(self, status, retval, task_id, args, kwargs, cinfo):
        collection_path = args[0]
        collection = Collection.from_identifier(Identifier(path=collection_path))
        # NOTE: collection is locked immediately after collection_signatures task
        #       starts in webui.views.collections.signatures
        collection.unlock(task_id)
        collection.cache_delete()
        gitstatus.update(settings.MEDIA_BASE, collection_path)
        gitstatus.unlock(settings.MEDIA_BASE, 'collection_signatures')

@task(base=CollectionSignaturesDebugTask, name='webui-collection-signatures')
def collection_signatures(collection_path, git_name, git_mail):
    """Identifies signature files for collection and entities.
    
    @param collection_path: Absolute path to collection repo.
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    @return collection_path: Absolute path to collection.
    """
    gitstatus.lock(settings.MEDIA_BASE, 'collection_signatures')
    collection = Collection.from_identifier(Identifier(path=collection_path))
    updates = signatures.find_updates(collection)
    files_written = signatures.write_updates(updates)
    
    status,msg = signatures.commit_updates(
        collection,
        files_written,
        git_name, git_mail, agent='ddr-local'
    )
    logger.debug('DONE')
    log.ok('Updating Elasticsearch')
    if settings.DOCSTORE_ENABLED:
        collection = Collection.from_identifier(Identifier(path=collection_path))
        try:
            collection.post_json()
        except ConnectionError:
            logger.error('Could not update search index')
    
    return collection_path


# ----------------------------------------------------------------------

TASK_STATUS_MESSAGES['webui-csv-export-model'] = {
    #'STARTED': '',
    'PENDING': 'Exporting {collection_id} {things} to CSV.',
    'SUCCESS': 'CSV file ready for download: <a href="{file_url}">{file_name}</a>.',
    'FAILURE': 'Could not export {collection_id} {things} to CSV.',
    #'RETRY': '',
    #'REVOKED': '',
}

class CSVExportDebugTask(Task):
    abstract = True
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        pass
    def on_success(self, retval, task_id, args, kwargs):
        pass
    def after_return(self, status, retval, task_id, args, kwargs, cinfo):
        pass

@task(base=CSVExportDebugTask, name='webui-csv-export-model')
def csv_export_model( collection_path, model ):
    """Export collection {model} metadata to CSV file.
    
    @return collection_path: Absolute path to collection.
    @return model: 'entity' or 'file'.
    """
    collection = Collection.from_identifier(Identifier(path=collection_path))
    csv_path = settings.CSV_EXPORT_PATH[model] % collection.id
    
    logger.info('All paths in %s' % collection_path)
    paths = util.find_meta_files(
        basedir=collection_path, model=model, recursive=1, force_read=1
    )
    logger.info('Exporting %s paths' % len(paths))
    batch.Exporter.export(
        paths, model, csv_path, required_only=False
    )
    return csv_path


# ----------------------------------------------------------------------

def session_tasks( request ):
    """Gets task statuses from Celery API, appends to task dicts from session.
    
    This function is used to generate the list of pending/successful/failed tasks
    in the webapp page notification area.
    
    @param request: A Django request object
    @return tasks: a dict with task_id for key
    """
    # basic tasks info from session:
    # task_id, action ('name' argument of @task), start time, args
    tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # add entity URLs
    for task_id in tasks.keys():
        task = tasks.get(task_id, None)
        if task and task['action'] in ['webui-file-new-master',
                                       'webui-file-new-mezzanine',
                                       'webui-file-new-access']:
                # Add entity_url to task for newly-created file
                task['entity_url'] = reverse('webui-entity', args=[task['entity_id']])
    # Hit the celery-task_status view for status updates on each task.
    # get status, retval from celery
    # TODO Don't create a new ctask/task dict here!!! >:-O
    traceback = None
    for task_id in tasks.keys():
        # Skip the HTTP and get directly from Celery API
        # djcelery.views.task_status
        result = AsyncResult(task_id)
        state, retval = result.state, result.result
        response_data = {'id': task_id, 'status': state, 'result': retval}
        if state in states.EXCEPTION_STATES:
            traceback = result.traceback
            response_data.update({'result': safe_repr(retval),
                                  'exc': get_full_cls_name(retval.__class__),
                                  'traceback': traceback})
        # end djcelery.views.task_status
        task = response_data
        # construct collection/entity/file urls if possible
        if task:
            ctask = tasks[task['id']]
            ctask['status'] = task.get('status', None)
            ctask['result'] = task.get('result', None)
            # try to convert 'result' into a collection/entity/file URL
            if (ctask['status'] != 'FAILURE') and ctask['result']:
                r = ctask['result']
                if type(r) == type({}):
                    if r.get('id', None):
                        oid = Identifier(r['id'])
                        object_url = reverse('webui-%s' % oid.model, args=[oid.id])
                        ctask['%s_url' % oid.model] = object_url
            tasks[task['id']] = ctask
    # pretty status messages
    for task_id in tasks.keys():
        task = tasks[task_id]
        action = task.get('action', None)
        if action:
            messages = TASK_STATUS_MESSAGES.get(action, None)
        status = task.get('status', None)
        template = None
        if messages and status:
            template = messages.get(status, None)
        if template:
            msg = template.format(**task)
            task['message'] = msg
    # indicate if task is dismiss or not
    for task_id in tasks.keys():
        task = tasks[task_id]
        if task.get('status', None):
            task['dismissable'] = (task['status'] in TASK_STATUSES_DISMISSABLE)
    # include traceback in task if present
    if traceback:
        task['traceback'] = traceback
    # done
    return tasks

def session_tasks_list( request ):
    """session_tasks as a list, sorted in reverse chronological order.
    
    NOTE: This function adds task['startd'], a datetime based on the str task['start'].
    
    @param request: A Django request object
    @return tasks: A list of task dicts.
    """
    return sorted(session_tasks(request).values(),
                  key=lambda t: t['start'],
                  reverse=True)

def dismiss_session_task( request, task_id ):
    """Dismiss a task from session_tasks.
    
    Removes 'startd' fields bc datetime objects not serializable to JSON.
    """
    newtasks = {}
    tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    for tid in tasks.keys():
        if tid != task_id:
            task = tasks[tid]
            if task.get('startd',None):
                task.pop('startd')
            newtasks[tid] = task
    request.session[settings.CELERY_TASKS_SESSION_KEY] = newtasks
