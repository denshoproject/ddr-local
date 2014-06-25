from datetime import datetime, timedelta
import json
import os

from celery import task
from celery import Task
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

import requests

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.urlresolvers import reverse

from migration.densho import export_entities, export_files, export_csv_path
from webui import get_repos_orgs
from webui.models import Collection, Entity, DDRFile
from webui.models import gitstatus_read

from DDR import docstore, models
from DDR.commands import entity_destroy, file_destroy
from DDR.commands import sync
from DDR.storage import is_writable



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
        'FAILURE': 'Could not upload <a href="{file_url}">{filename}</a> to <a href="{entity_url}">{entity_id}</a>.',
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
        logger.debug('ElasticsearchTask.after_return(%s, %s, %s, %s, %s)' % (status, retval, task_id, args, kwargs))

@task(base=ElasticsearchTask, name='webui-search-reindex')
def reindex( index ):
    """
    @param index: Name of index to create or update
    """
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



class GitStatusTask(Task):
    abstract = True
        
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.debug('GitStatusTask.on_failure(%s, %s, %s, %s, %s)' % (exc, task_id, args, kwargs, einfo))
        _gitstatus_log('GitStatusTask.on_failure(%s, %s, %s, %s, %s)' % (exc, task_id, args, kwargs, einfo))
    
    def on_success(self, retval, task_id, args, kwargs):
        logger.debug('GitStatusTask.on_success(%s, %s, %s, %s)' % (retval, task_id, args, kwargs))
        _gitstatus_log('GitStatusTask.on_success(%s, %s, %s, %s)' % (retval, task_id, args, kwargs))
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        logger.debug('GitStatusTask.after_return(%s, %s, %s, %s, %s, %s)' % (status, retval, task_id, args, kwargs, einfo))
        _gitstatus_log('GitStatusTask.after_return(%s, %s, %s, %s, %s, %s)' % (status, retval, task_id, args, kwargs, einfo))

# Records gitstatus-update activity
GITSTATUS_LOG = '/var/log/ddr/gitstatus.log'

# Paths to collection repos to be updated, and timestamps of last update.
GITSTATUS_QUEUE_PATH = os.path.join(settings.MEDIA_BASE, '.gitstatus-queue')

# Processes that should not be interrupted by gitstatus-update should
# write something to this file (doesn't matter what) and remove the file
# when they are finished.
GITSTATUS_LOCK_PATH = os.path.join(settings.MEDIA_BASE, '.gitstatus-stop')

# Minimum interval between git-status updates per collection repository.
GITSTATUS_INTERVAL = 60*2

GITSTATUS_BACKOFF = 30

def _gitstatus_log(msg):
    """celery does not like writing to logs, so write to separate logfile
    """
    entry = '%s %s\n' % (datetime.now().strftime(settings.TIMESTAMP_FORMAT), msg)
    with open(GITSTATUS_LOG, 'a') as f:
        f.write(entry)

def _gitstatus_next_repo():
    """Gets next collection_path or time til next ready to be updated
    
    Each line of GITSTATUS_QUEUE_PATH contains a collection_path and
    a timestamp of the last time git-status was done on the collection.
    Timestamps come from .gitstatus files in the collection repos.
    If a repo has no .gitstatus file then date in past is used (e.g. update now).
    The first collection with a timestamp more than GITSTATUS_INTERVAL
    in the past is returned.
    If there are collections but they are too recent a 'notready'
    message is returned along with the time til next is available.
    
    Sample file 0:
        [empty]
    
    Sample file 1:
        /var/www/media/base/ddr-densho-252 2014-06-24T1503:22-07:00
        /var/www/media/base/ddr-densho-255 2014-06-24T1503:22-07:00
        /var/www/media/base/ddr-densho-282 2014-06-24T1503:22-07:00
    
    @returns: collection_path or (msg,timedelta)
    """
    # load existing queue; populate queue if empty
    contents = ''
    if os.path.exists(GITSTATUS_QUEUE_PATH):
        with open(GITSTATUS_QUEUE_PATH, 'r') as f:
            contents = f.read()
    lines = []
    for line in contents.strip().split('\n'):
        line = line.strip()
        if line:
            lines.append(line)
    if not lines:
        # refresh
        for o in get_repos_orgs():
            repo,org = o.split('-')
            paths = Collection.collections(settings.MEDIA_BASE, repository=repo, organization=org)
            for path in paths:
                # get time repo gitstatus last update
                # if no gitstatus file, make immediately updatable
                gitstat = gitstatus_read(path)
                if gitstat:
                    timestamp,elapsed,status,annex_status,sync_status = gitstat
                    ts = timestamp.strftime(settings.TIMESTAMP_FORMAT)
                else:
                    ts = datetime.fromtimestamp(0).strftime(settings.TIMESTAMP_FORMAT)
                line = ' '.join([path, ts])
                lines.append(line)
#    # if backoff leave the queue file as is
#    gitstatus_backoff = timedelta(seconds=GITSTATUS_BACKOFF)
#    for n,line in enumerate(lines):
#        if 'backoff' in line:
#            msg,ts = line.split(' ')
#            timestamp = datetime.strptime(ts, settings.TIMESTAMP_FORMAT)
#            elapsed = datetime.now() - timestamp
#            if elapsed < gitstatus_backoff:
#                # not enough time elapsed: die
#                delay = gitstatus_backoff - elapsed
#                return 'backoff',delay
#            else:
#                # enough time has passed: rm the backoff
#                lines.remove(line)
    # any eligible collections?
    eligible = []
    gitstatus_interval = timedelta(seconds=GITSTATUS_INTERVAL)
    delay = gitstatus_interval
    for line in lines:
        path,ts = line.split(' ')
        timestamp = datetime.strptime(ts, settings.TIMESTAMP_FORMAT)
        elapsed = datetime.now() - timestamp
        if elapsed > gitstatus_interval:
            eligible.append(line)
        else:
            # report smallest interval (e.g. next possible update time)
            wait = gitstatus_interval - elapsed
            if wait < delay:
               delay = wait
    # we have collections
    if lines:
        if eligible:
            # eligible collections - pop the first one off the queue
            for line in lines:
                if line == eligible[0]:
                    lines.remove(line)
            text = '\n'.join(lines) + '\n'
            with open(GITSTATUS_QUEUE_PATH, 'w') as f1:
                f1.write(text)
            collection_path,ts = eligible[0].split(' ')
            return collection_path
        else:
#            # collections but none eligible: back off!
#            timestamp = datetime.now()
#            backoff = 'backoff %s' % timestamp.strftime(settings.TIMESTAMP_FORMAT)
#            lines.insert(0, backoff)
            text = '\n'.join(lines) + '\n'
            with open(GITSTATUS_QUEUE_PATH, 'w') as f1:
                f1.write(text)
            return 'notready',delay
    return None

@task(base=GitStatusTask, name='webui.tasks.gitstatus_update')
def gitstatus_update():
    """
    
    - Ensures only one gitstatus_update task running at a time
    - Checks to make sure MEDIA_BASE is readable and that no
      other process has requested a lock.
    - Pulls next collection_path off the queue.
    - Triggers a gitstatus update/write
    - 
    
    Reference: Ensuring only one gitstatus_update runs at a time
    http://docs.celeryproject.org/en/latest/tutorials/task-cookbook.html#cookbook-task-serial
    
    @returns: success/fail message
    """
    _gitstatus_log('gitstatus_update() ---------------------')
    GITSTATUS_LOCK_ID = 'gitstatus-update-lock'
    GITSTATUS_LOCK_EXPIRE = 60 * 5
    acquire_lock = lambda: cache.add(GITSTATUS_LOCK_ID, 'true', GITSTATUS_LOCK_EXPIRE)
    release_lock = lambda: cache.delete(GITSTATUS_LOCK_ID)
    #logger.debug('git status: %s', collection_path)
    message = None
    if acquire_lock():
        _gitstatus_log('celery lock acquired')
        try:
            writable = is_writable(settings.MEDIA_BASE)
            locked = os.path.exists(GITSTATUS_LOCK_PATH)
            if locked:
                _gitstatus_log('locked by another celery process')
                message = 'locked by another process'
            elif writable:
                response = _gitstatus_next_repo()
                _gitstatus_log(response)
                if isinstance(response, list) or isinstance(response, tuple):
                    message = str(response)
                else:
                    collection_path = response
                    collection = Collection.from_json(collection_path)
                    timestamp,elapsed,status,annex_status,sync_status = collection.gitstatus(force=True)
                    _gitstatus_log(timestamp)
                    _gitstatus_log(status)
                    _gitstatus_log(annex_status[72])
                    message = '%s updated in %s' % (collection_path, str(elapsed))
            else:
                _gitstatus_log('MEDIA_BASE not writable!')
                message = 'MEDIA_BASE not writable!'
        finally:
            release_lock()
            _gitstatus_log('celery lock released')
    else:
        _gitstatus_log("couldn't get celery lock")
        message = "couldn't get celery lock"
        #logger.debug('git-status: another worker already running')
    #return 'git-status: another worker already running'
    return message


class FileAddDebugTask(Task):
    abstract = True
        
    def on_failure(self, exception, task_id, args, kwargs, einfo):
        entity = args[2]
        entity.files_log(0,'DDRTask.ON_FAILURE')
    
    def on_success(self, retval, task_id, args, kwargs):
        entity = args[2]
        entity.files_log(1,'DDRTask.ON_SUCCESS')
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        entity = args[2]
        entity.files_log(1,'DDRTask.AFTER_RETURN')
        entity.files_log(1,'task_id: %s' % task_id)
        entity.files_log(1,'status: %s' % status)
        entity.files_log(1,'retval: %s' % retval)
        entity.files_log(1,'Unlocking %s' % entity.id)
        lockstatus = entity.unlock(task_id)
        if lockstatus == 'ok':
            entity.files_log(1,'unlocked')
        else:
            entity.files_log(0,lockstatus)
        entity.files_log(1, 'END task_id %s\n' % task_id)
        collection = Collection.from_json(Collection.collection_path(None,entity.repo,entity.org,entity.cid))
        collection.cache_delete()

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
    return entity.add_file(git_name, git_mail, src_path, role, data, agent)

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
    return entity.add_access(git_name, git_mail, ddrfile, agent)



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
        'collection_url': collection.url(),
        'collection_id': collection.id,
        'entity_url': entity.url(),
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
        collection = Collection.from_json(collection_path)
        lockstatus = collection.unlock(task_id)

@task(base=DeleteEntityTask, name='webui-entity-delete')
def delete_entity( git_name, git_mail, collection_path, entity_id, agent='' ):
    """
    @param collection_path: string
    @param entity_id: string
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    @param agent: (optional) Name of software making the change.
    """
    logger.debug('collection_delete_entity(%s,%s,%s,%s,%s)' % (git_name, git_mail, collection_path, entity_id, agent))
    status,message = entity_destroy(git_name, git_mail, collection_path, entity_id, agent)
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
        'entity_url': entity.url(),
        'entity_id': entity.id,
        'filename': file_.basename,
        'file_url': file_.url(),
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
        collection = Collection.from_json(collection_path)
        lockstatus = collection.unlock(task_id)

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
    # TODO rm_files list should come from the File model
    file_id = os.path.splitext(file_basename)[0]
    repo,org,cid,eid,role,sha1 = file_id.split('-')
    entity = DDREntity.from_json(DDREntity.entity_path(None,repo,org,cid,eid))
    file_ = entity.file(repo, org, cid, eid, role, sha1)
    rm_files = file_.files_rel(collection_path)
    logger.debug('rm_files: %s' % rm_files)
    # remove file from entity.json
    # TODO move this to commands.file_destroy or models.Entity
    for f in entity.files:
        if f.basename == file_basename:
            entity.files.remove(f)
    entity.dump_json()
    updated_files = ['entity.json']
    logger.debug('updated_files: %s' % updated_files)
    status,message = file_destroy(git_name, git_mail, collection_path, entity_id, rm_files, updated_files, agent)
    return status,message,collection_path,file_basename



class CollectionSyncDebugTask(Task):
    abstract = True
    
    def on_failure(self, exc, task_id, args, kwargs):
        pass
    
    def on_success(self, retval, task_id, args, kwargs):
        pass
    
    def after_return(self, status, retval, task_id, args, kwargs, cinfo):
        collection_path = args[2]
        collection = Collection.from_json(collection_path)
        # NOTE: collection is locked immediately after collection_sync task
        #       starts in webui.views.collections.sync
        collection.unlock(task_id)
        collection.cache_delete()

@task(base=CollectionSyncDebugTask, name='collection-sync')
def collection_sync( git_name, git_mail, collection_path ):
    """Synchronizes collection repo with workbench server.
    
    @param src_path: Absolute path to collection repo.
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    @return collection_path: Absolute path to collection.
    """
    exit,status = sync(git_name, git_mail, collection_path)
    # update search index
    path = os.path.join(collection_path, 'collection.json')
    with open(path, 'r') as f:
        document = json.loads(f.read())
    docstore.post(settings.DOCSTORE_HOSTS, settings.DOCSTORE_INDEX, document)
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
    def on_failure(self, exc, task_id, args, kwargs):
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
        # hit the celery API for each task
        url = 'http://127.0.0.1%s' % reverse('celery-task_status', args=[task_id])
        r = requests.get(url)
        # if there's a traceback, save for later (see below)
        try:
            data = r.json()
            if data.get('task', None) and data['task'].get('traceback', None):
                traceback = data['task']['traceback']
            task = data['task']
        except:
            task = None
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
    """
    newtasks = {}
    tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    for tid in tasks.keys():
        if tid != task_id:
            newtasks[tid] = tasks[tid]
    request.session[settings.CELERY_TASKS_SESSION_KEY] = newtasks
