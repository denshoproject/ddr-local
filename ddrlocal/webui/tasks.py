from datetime import datetime, timedelta
import json
import os

from celery import task
from celery import Task
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from celery import states
from celery.result import AsyncResult
from celery.utils.encoding import safe_repr
from celery.utils import get_full_cls_name
import requests

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.urlresolvers import reverse

from migration.densho import export_entities, export_files, export_csv_path
from webui import GITOLITE_INFO_CACHE_KEY
from webui import gitolite
from webui import gitstatus
from webui.models import Collection, Entity, DDRFile, post_json
from webui.identifier import Identifier

from DDR import docstore
from DDR import dvcs
from DDR import models
from DDR.commands import entity_destroy, file_destroy
from DDR.commands import sync



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
    if not os.path.exists(settings.MEDIA_BASE):
        raise NameError('MEDIA_BASE does not exist - you need to remount!')
    logger.debug('webui.tasks.reindex(%s)' % index)
    logger.debug('DOCSTORE_HOSTS: %s' % settings.DOCSTORE_HOSTS)
    logger.debug('- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - ')
    logger.debug('deleting existing index: %s' % index)
    delete_status = docstore.delete_index(settings.DOCSTORE_HOSTS, index)
    logger.debug(delete_status)
    logger.debug('- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - ')
    logger.debug('creating new index: %s' % index)
    create_status = docstore.create_index(settings.DOCSTORE_HOSTS, index)
    logger.debug(create_status)
    logger.debug('- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - ')
    logger.debug('mappings: %s, %s' % (docstore.HARD_CODED_MAPPINGS_PATH, models.MODELS_DIR))
    mappings_status = docstore.put_mappings(settings.DOCSTORE_HOSTS, index,
                                            docstore.HARD_CODED_MAPPINGS_PATH, models.MODELS_DIR)
    logger.debug(mappings_status)
    logger.debug('- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - ')
    logger.debug('facets')
    facets_status = docstore.put_facets(settings.DOCSTORE_HOSTS, index)
    logger.debug(facets_status)
    logger.debug('- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - ')
    logger.debug('indexing')
    index_status = docstore.index(settings.DOCSTORE_HOSTS, index, path=settings.MEDIA_BASE,
                                  recursive=True, public=False)
    logger.debug(index_status)
    return statuses

def reindex_and_notify( index ):
    """Drop existing index and build another from scratch; hand off to Celery.
    This function is intended for use in a view.
    """
    result = reindex(index).apply_async(countdown=2)
    celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
    task = {'task_id': result.task_id,
            'action': 'webui-search-reindex',
            'index': index,
            'start': datetime.now().strftime(settings.TIMESTAMP_FORMAT),}
    celery_tasks[result.task_id] = task
    request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks



@task(base=DebugTask, name='webui.tasks.gitolite_info_refresh')
def gitolite_info_refresh():
    """
    Check the cached value of DDR.dvcs.gitolite_info().
    If it is stale (e.g. timestamp is older than cutoff)
    then hit the Gitolite server for an update and re-cache.
    """
    return gitolite.refresh()



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


class FileAddDebugTask(Task):
    abstract = True
        
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        entity = args[2]
        log = entity.addfile_logger()
        log.not_ok('DDRTask.ON_FAILURE')
    
    def on_success(self, retval, task_id, args, kwargs):
        entity = args[2]
        log = entity.addfile_logger()
        log.ok('DDRTask.ON_SUCCESS')
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        entity = args[2]
        collection = entity.collection()
        log = entity.addfile_logger()
        log.ok('DDRTask.AFTER_RETURN')
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
        gitstatus.update(settings.MEDIA_BASE, collection_path)
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
    file_,repo,log = entity.add_file(src_path, role, data, git_name, git_mail, agent)
    file_,repo,log = entity.add_file_commit(file_, repo, log, git_name, git_mail, agent)
    post_json(settings.DOCSTORE_HOSTS, settings.DOCSTORE_INDEX, file_.json_path)
    return file_.__dict__

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
    file_,repo,log = entity.add_access(ddrfile, git_name, git_mail, agent)
    return file_.__dict__



# ----------------------------------------------------------------------

TASK_STATUS_MESSAGES['webui-collection-newexpert'] = {
    #'STARTED': '',
    'PENDING': 'Creating new collection <b>{collection_id}</b>...',
    'SUCCESS': 'Created new collection <b><a href="{collection_url}">{collection_id}</a></b>.',
    'FAILURE': 'Could not create new collection <b>{collection_id}</b>.',
    #'RETRY': '',
    #'REVOKED': '',
}

def collection_new_expert(request, base_dir, collection_id, git_name, git_mail):
    # start tasks
    repo,org,cid = collection_id.split('-')
    collection_path = os.path.join(base_dir, collection_id)
    collection_url = reverse('webui-collection', args=[repo,org,cid])
    result = collection_newexpert.apply_async(
        (collection_path, git_name, git_mail),
        countdown=2)
    # add celery task_id to session
    celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
    celery_tasks[result.task_id] = {
        'task_id': result.task_id,
        'action': 'webui-collection-newexpert',
        'collection_url': collection_url,
        'collection_id': collection_id,
        'start': datetime.now().strftime(settings.TIMESTAMP_FORMAT),}
    request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks

class CollectionNewExpertTask(Task):
    abstract = True
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        logger.debug('CollectionNewExpertTask.after_return(%s, %s, %s, %s, %s)' % (status, retval, task_id, args, kwargs))
        collection_path = args[0]
        collection = Collection.from_identifier(Identifier(path=collection_path))
        lockstatus = collection.unlock(task_id)
        gitstatus.update(settings.MEDIA_BASE, collection_path)
        gitstatus.unlock(settings.MEDIA_BASE, 'collection_newexpert')

@task(base=CollectionNewExpertTask, name='webui-collection-newexpert')
def collection_newexpert(collection_path, git_name, git_mail):
    """Create new collection using known ID.
    
    @param collection_path: str Absolute path to collection
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    """
    logger.debug('collection_newexpert(%s,%s,%s)' % (
        collection_path, git_name, git_mail))
    
    collection = Collection.create(collection_path, git_name, git_mail)
    gitstatus_update.apply_async((collection.path,), countdown=2)
    
    return 'status',collection_path

# ----------------------------------------------------------------------

TASK_STATUS_MESSAGES['webui-collection-edit'] = {
    #'STARTED': '',
    'PENDING': 'Saving changes to collection <b><a href="{collection_url}">{collection_id}</a></b>...',
    'SUCCESS': 'Saved changes to collection <b><a href="{collection_url}">{collection_id}</a></b>.',
    'FAILURE': 'Could not save changes to collection <b><a href="{collection_url}">{collection_id}</a></b>.',
    #'RETRY': '',
    #'REVOKED': '',
}

def collection_edit(request, collection, updated_files, git_name, git_mail):
    # start tasks
    result = collection_save.apply_async(
        (collection.path, updated_files, git_name, git_mail),
        countdown=2)
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
        'start': datetime.now().strftime(settings.TIMESTAMP_FORMAT),}
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
def collection_save(collection_path, updated_files, git_name, git_mail):
    """The time-consuming parts of collection-edit.
    
    @param collection_path: str Absolute path to collection
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    """
    logger.debug('collection_save(%s,%s,%s,%s)' % (
        git_name, git_mail, collection_path, updated_files))
    
    collection = Collection.from_identifier(Identifier(path=collection_path))
    
    gitstatus.lock(settings.MEDIA_BASE, 'collection_edit')
    exit,status = collection.save(updated_files, git_name, git_mail)
    gitstatus_update.apply_async((collection_path,), countdown=2)
    
    return status,collection_path

# ----------------------------------------------------------------------

TASK_STATUS_MESSAGES['webui-entity-newexpert'] = {
    #'STARTED': '',
    'PENDING': 'Creating new object <b>{entity_id}</b>...',
    'SUCCESS': 'Created new object <b><a href="{entity_url}">{entity_id}</a></b>.',
    'FAILURE': 'Could not create new object <b>{entity_id}</b>.',
    #'RETRY': '',
    #'REVOKED': '',
}

def collection_entity_newexpert(request, collection, entity_id, git_name, git_mail):
    # start tasks
    repo,org,cid,eid = entity_id.split('-')
    entity_url = reverse('webui-entity', args=[repo,org,cid,eid])
    result = entity_newexpert.apply_async(
        (collection.path, entity_id, git_name, git_mail),
        countdown=2)
    # lock collection
    lockstatus = collection.lock(result.task_id)
    # add celery task_id to session
    celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
    celery_tasks[result.task_id] = {
        'task_id': result.task_id,
        'action': 'webui-entity-newexpert',
        'collection_url': collection.absolute_url(),
        'collection_id': collection.id,
        'entity_url': entity_url,
        'entity_id': entity_id,
        'start': datetime.now().strftime(settings.TIMESTAMP_FORMAT),}
    request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks

class EntityNewExpertTask(Task):
    abstract = True
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.debug('EntityNewExpertTask.on_failure(%s, %s, %s, %s)' % (exc, task_id, args, kwargs))
    
    def on_success(self, retval, task_id, args, kwargs):
        logger.debug('EntityNewExpertTask.on_success(%s, %s, %s, %s)' % (retval, task_id, args, kwargs))
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        logger.debug('EntityNewExpertTask.after_return(%s, %s, %s, %s, %s)' % (status, retval, task_id, args, kwargs))
        collection_path = args[0]
        collection = Collection.from_identifier(Identifier(path=collection_path))
        lockstatus = collection.unlock(task_id)
        gitstatus.update(settings.MEDIA_BASE, collection_path)
        gitstatus.unlock(settings.MEDIA_BASE, 'entity_newexpert')

@task(base=EntityNewExpertTask, name='webui-entity-newexpert')
def entity_newexpert(collection_path, entity_id, git_name, git_mail):
    """Create new entity using known entity ID.
    
    @param collection_path: str Absolute path to collection
    @param entity_id: str
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    """
    logger.debug('collection_entity_newexpert(%s,%s,%s,%s)' % (
        collection_path, entity_id, git_name, git_mail))
    
    collection = Collection.from_identifier(Identifier(path=collection_path))
    
    gitstatus.lock(settings.MEDIA_BASE, 'entity_newexpert')
    entity = Entity.create(collection, entity_id, git_name, git_mail)
    gitstatus_update.apply_async((collection.path,), countdown=2)

    return 'status',collection_path,entity.id

# ----------------------------------------------------------------------

TASK_STATUS_MESSAGES['webui-file-edit'] = {
    #'STARTED': '',
    'PENDING': 'Saving changes to file <b><a href="{file_url}">{file_id}</a></b>...',
    'SUCCESS': 'Saved changes to file <b><a href="{file_url}">{file_id}</a></b>.',
    'FAILURE': 'Could not save changes to file <b><a href="{file_url}">{file_id}</a></b>.',
    #'RETRY': '',
    #'REVOKED': '',
}

def entity_file_edit(request, collection, file_, git_name, git_mail):
    # start tasks
    result = file_edit.apply_async(
        (collection.path, file_.id, git_name, git_mail),
        countdown=2)
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
        'start': datetime.now().strftime(settings.TIMESTAMP_FORMAT),}
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

@task(base=FileEditTask, name='webui-file-edit')
def file_edit(collection_path, file_id, git_name, git_mail):
    """The time-consuming parts of file-edit.
    
    @param collection_path: str Absolute path to collection
    @param file_id: str
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    """
    logger.debug('file_edit(%s,%s,%s,%s)' % (git_name, git_mail, collection_path, file_id))
    fidentifier = Identifier(id=file_id)
    file_ = DDRFile.from_identifier(fidentifier)
    gitstatus.lock(settings.MEDIA_BASE, 'file_edit')
    exit,status = file_.save(git_name, git_mail)
    gitstatus_update.apply_async((collection_path,), countdown=2)
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

def collection_entity_edit(request, collection, entity, updated_files, git_name, git_mail, agent):
    # start tasks
    result = entity_edit.apply_async(
        (collection.path, entity.id, updated_files, git_name, git_mail, agent),
        countdown=2)
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
        'updated_files': updated_files,
        'start': datetime.now().strftime(settings.TIMESTAMP_FORMAT),}
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
def entity_edit(collection_path, entity_id, updated_files, git_name, git_mail, agent=''):
    """The time-consuming parts of entity-edit.
    
    @param collection_path: str Absolute path to collection
    @param entity_id: str
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    @param agent: (optional) Name of software making the change.
    """
    logger.debug('collection_entity_edit(%s,%s,%s,%s,%s)' % (
        git_name, git_mail, collection_path, entity_id, agent))
    collection = Collection.from_identifier(Identifier(path=collection_path))
    entity = Entity.from_identifier(Identifier(id=entity_id))
    gitstatus.lock(settings.MEDIA_BASE, 'entity_edit')
    exit,status = entity.save_part2(updated_files, collection, git_name, git_mail)
    gitstatus_update.apply_async((collection.path,), countdown=2)
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
        countdown=2)
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
        'start': datetime.now().strftime(settings.TIMESTAMP_FORMAT),}
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
    status,message = entity_destroy(git_name, git_mail, collection_path, entity_id, agent)
    # update search index
    docstore.delete(settings.DOCSTORE_HOSTS, settings.DOCSTORE_INDEX, entity_id)
    return status,message,collection_path,entity_id



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
        countdown=2)
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
        'start': datetime.now().strftime(settings.TIMESTAMP_FORMAT),}
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
    # TODO rm_files list should come from the File model
    file_id = os.path.splitext(file_basename)[0]
    file_ = DDRFile.from_identifier(Identifier(id=file_id))
    entity = Entity.from_identifier(Identifier(id=entity_id))
    rm_files = file_.files_rel(collection_path)
    logger.debug('rm_files: %s' % rm_files)
    # remove file from entity.json
    # TODO move this to commands.file_destroy or models.Entity
    for f in entity.files:
        if f['path_rel'] == file_basename:
            entity.files.remove(f)
    entity.write_json()
    updated_files = ['entity.json']
    logger.debug('updated_files: %s' % updated_files)
    # remove the file itself
    status,message = file_destroy(git_name, git_mail, collection_path, entity_id, rm_files, updated_files, agent)
    # update search index
    docstore.delete(settings.DOCSTORE_HOSTS, settings.DOCSTORE_INDEX, file_id)
    return status,message,collection_path,file_basename



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
    exit,status = sync(git_name, git_mail, collection_path)
    # update search index
    collection = Collection.from_identifier(Identifier(path=collection_path))
    collection.post_json(settings.DOCSTORE_HOSTS, settings.DOCSTORE_INDEX)
    return collection_path



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
    csv_path = export_csv_path(collection_path, model)
    if model == 'entity':
        csv_path = export_entities(collection_path, csv_path)
    elif model == 'file':
        csv_path = export_files(collection_path, csv_path)
    return csv_path



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
                repo,org,cid,eid = task['entity_id'].split('-')
                task['entity_url'] = reverse('webui-entity', args=[repo,org,cid,eid])
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
                    if r.get('sha1', None):
                        url = reverse('webui-file',
                                      args=[ctask['result']['repo'],
                                            ctask['result']['org'],
                                            ctask['result']['cid'],
                                            ctask['result']['eid'],
                                            ctask['result']['role'],
                                            ctask['result']['sha1'],])
                        ctask['file_url'] = url
                    elif r.get('eid', None):
                        url = reverse('webui-entity',
                                      args=[ctask['result']['repo'],
                                            ctask['result']['org'],
                                            ctask['result']['cid'],
                                            ctask['result']['eid'],])
                        ctask['entity_url'] = url
                    elif r.get('cid', None):
                        url = reverse('webui-collection',
                                      args=[ctask['result']['repo'],
                                            ctask['result']['org'],
                                            ctask['result']['cid'],])
                        ctask['collection_url'] = url
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
