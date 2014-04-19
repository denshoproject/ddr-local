from datetime import datetime
import json
import os
import shutil

from celery import task
from celery import Task
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

import requests

from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse

from ddrlocal.models import DDRLocalEntity, DDRLocalFile, hash
from webui.models import Collection

from DDR import docstore
from DDR import dvcs
from DDR import inventory
from DDR.commands import clone, entity_annex_add, entity_update, sync
from DDR import models



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
        'FAILURE': 'Could not upload <a href="{file_url}">{filename}</a> to <a href="{entity_url}">{entity_id}</a>.',
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
    'webui-collection-refresh': {
        #'STARTED': '',
        'PENDING': 'Refreshing cached info for <b><a href="{collection_url}">{collection_id}</a></b>.',
        'SUCCESS': 'Refreshed cached info for <b><a href="{collection_url}">{collection_id}</a></b>.',
        'FAILURE': 'Could not refresh cached info for <b><a href="{collection_url}">{collection_id}</a></b>.',
        #'RETRY': '',
        #'REVOKED': '',
        },
    'webui-inventory-clone': {
        #'STARTED': '',
        'PENDING': 'clone PENDING',
        'SUCCESS': 'clone SUCCESS',
        'FAILURE': 'clone FAILURE',
        #'RETRY': '',
        #'REVOKED': '',
        },
    'webui-inventory-drop': {
        #'STARTED': '',
        'PENDING': 'drop PENDING',
        'SUCCESS': 'drop SUCCESS',
        'FAILURE': 'drop FAILURE',
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



class FileAddDebugTask(Task):
    abstract = True
        
    def on_failure(self, exc, task_id, args, kwargs, einfo):
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
    @param entity: DDRLocalEntity
    @param src_path: Absolute path to an uploadable file.
    @param role: Keyword of a file role.
    @param data: Dict containing form data.
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    @param agent: (optional) Name of software making the change.
    """
    file_ = add_file(git_name, git_mail, entity, src_path, role, data, agent)
    return file_


def add_file( git_name, git_mail, entity, src_path, role, data, agent='' ):
    """Add file to entity
    
    This method breaks out of OOP and manipulates entity.json directly.
    Thus it needs to lock to prevent other edits while it does its thing.
    Writes a log to ${entity}/addfile.log, formatted in pseudo-TAP.
    This log is returned along with a DDRLocalFile object.
    
    @param entity: DDRLocalEntity
    @param src_path: Absolute path to an uploadable file.
    @param role: Keyword of a file role.
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    @param agent: (optional) Name of software making the change.
    @return file_ DDRLocalFile object
    """
    f = None
                
    entity.files_log(1, 'ddrlocal.webui.tasks.add_file: START')
    entity.files_log(1, 'entity: %s' % entity.id)
    entity.files_log(1, 'data: %s' % data)
    
    src_basename      = os.path.basename(src_path)
    src_exists        = os.path.exists(src_path)
    src_readable      = os.access(src_path, os.R_OK)
    if not os.path.exists(entity.files_path):
        os.mkdir(entity.files_path)
    dest_dir          = entity.files_path
    dest_dir_exists   = os.path.exists(dest_dir)
    dest_dir_writable = os.access(dest_dir, os.W_OK)
    dest_basename     = DDRLocalFile.file_name(entity, src_path, role)
    dest_path         = os.path.join(dest_dir, dest_basename)
    dest_path_exists  = os.path.exists(dest_path)
    s = []
    if src_exists:         s.append('ok')
    else:                  entity.files_log(0, 'Source file does not exist: {}'.format(src_path))
    if src_readable:       s.append('ok')
    else:                  entity.files_log(0, 'Source file not readable: {}'.format(src_path))
    if dest_dir_exists:    s.append('ok')
    else:                  entity.files_log(0, 'Destination directory does not exist: {}'.format(dest_dir))
    if dest_dir_writable:  s.append('ok')
    else:                  entity.files_log(0, 'Destination directory not writable: {}'.format(dest_dir))
    #if not dest_path_exists: s.append('ok')
    #else:                  entity.files_log(0, 'Destination file already exists!: {}'.format(dest_path))
    preparations = ','.join(s)
    
    # do, or do not
    cp_successful = False
    if preparations == 'ok,ok,ok,ok':  # ,ok
        entity.files_log(1, 'Source file exists; is readable.  Destination dir exists, is writable.')
        entity.files_log(1, 'src file size: %s' % os.path.getsize(src_path))
        # task: copy
        entity.files_log(1, 'cp %s %s' % (src_path, dest_path))
        try:
            shutil.copy(src_path, dest_path)
        except:
            # TODO would be nice to know why copy failed
            entity.files_log(0, 'copy FAIL')
        if os.path.exists(dest_path):
            cp_successful = True
            entity.files_log(1, 'copy ok')
    
    # file object
    if cp_successful:
        f = DDRLocalFile(dest_path)
        entity.files_log(1, 'Created DDRLocalFile: %s' % f)
        f.basename_orig = src_basename
        entity.files_log(1, 'Original filename: %s' % f.basename_orig)
        f.role = role
        # form data
        for field in data:
            setattr(f, field, data[field])
        f.size = os.path.getsize(f.path_abs)
        entity.files_log(1, 'dest file size: %s' % f.size)
        # task: get SHA1 checksum (links entity.filemeta entity.files records
        entity.files_log(1, 'Checksumming...')
        try:
            f.sha1   = hash(src_path, 'sha1')
            entity.files_log(1, 'sha1: %s' % f.sha1)
        except:
            entity.files_log(0, 'sha1 FAIL')
        try:
            f.md5    = hash(src_path, 'md5')
            entity.files_log(1, 'md5: %s' % f.md5)
        except:
            entity.files_log(0, 'md5 FAIL')
        try:
            f.sha256 = hash(src_path, 'sha256')
            entity.files_log(1, 'sha256: %s' % f.sha256)
        except:
            entity.files_log(0, 'sha256 FAIL')
        # task: extract_xmp
        entity.files_log(1, 'Extracting XMP data...')
        try:
            f.xmp = DDRLocalFile.extract_xmp(src_path)
            if f.xmp:
                entity.files_log(1, 'got some XMP')
            else:
                entity.files_log(1, 'no XMP data')
        except:
            # TODO would be nice to know why XMP extract failed
            entity.files_log(0, 'XMP extract FAIL')
    
    # access file
    if f and cp_successful:
        # task: make access file
        entity.files_log(1, 'Making access file...')
        # NOTE: do this before entity_annex_add so don't have to lock/unlock
        status,result = DDRLocalFile.make_access_file(f.path_abs,
                                                 settings.ACCESS_FILE_APPEND,
                                                 settings.ACCESS_FILE_GEOMETRY,
                                                 settings.ACCESS_FILE_OPTIONS)
        if status:
            entity.files_log(0, 'access file FAIL: %s' % result)
            f.access_rel = None
        else:
            access_rel = result
            f.set_access(access_rel, entity)
            entity.files_log(1, 'access_rel: %s' % f.access_rel)
            entity.files_log(1, 'access_abs: %s' % f.access_abs)
    
    # dump metadata, commit
    if f and cp_successful:
        entity.files_log(1, 'Adding %s to entity...' % f)
        entity.files.append(f)
        entity.dump_json()
        f.dump_json()
        
        git_files = [entity.json_path_rel, f.json_path_rel]
        annex_files = [f.basename]
        if f.access_rel:
            annex_files.append(os.path.basename(f.access_rel))
        
        entity.files_log(1, 'entity_annex_add(%s, %s, %s, %s, %s, %s, %s)' % (
            git_name, git_mail,
            entity.parent_path, entity.id,
            git_files, annex_files,
            agent))
        exit,status = entity_annex_add(git_name, git_mail,
                                       entity.parent_path, entity.id,
                                       git_files, annex_files,
                                       agent=agent)
        entity.files_log(1, 'entity_annex_add: exit: %s' % exit)
        entity.files_log(1, 'entity_annex_add: status: %s' % status)
        
    entity.files_log(1, 'ddrlocal.webui.tasks.add_file: FINISHED')
    return f.__dict__





@task(base=FileAddDebugTask, name='entity-add-access')
def entity_add_access( git_name, git_mail, entity, ddrfile, agent='' ):
    """
    @param entity: DDRLocalEntity
    @param ddrfile: DDRLocalFile
    @param src_path: Absolute path to an uploadable file.
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    @param agent: (optional) Name of software making the change.
    """
    file_ = add_access(git_name, git_mail, entity, ddrfile, agent)
    return file_


def add_access( git_name, git_mail, entity, ddrfile, agent='' ):
    """Generate new access file for entity
    
    This method breaks out of OOP and manipulates entity.json directly.
    Thus it needs to lock to prevent other edits while it does its thing.
    Writes a log to ${entity}/addfile.log, formatted in pseudo-TAP.
    This log is returned along with a DDRLocalFile object.
    
    @param entity: DDRLocalEntity
    @param ddrfile: DDRLocalFile
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    @return file_ DDRLocalFile object
    @param agent: (optional) Name of software making the change.
    """
    f = ddrfile
    src_path = f.path_abs
    
    entity.files_log(1, 'ddrlocal.webui.tasks.add_access: START')
    entity.files_log(1, 'entity: %s' % entity.id)
    entity.files_log(1, 'src: %s' % f.path_rel)
    
    src_basename      = os.path.basename(src_path)
    src_exists        = os.path.exists(src_path)
    src_readable      = os.access(src_path, os.R_OK)
    if not os.path.exists(entity.files_path):
        os.mkdir(entity.files_path)
    dest_dir          = entity.files_path
    dest_dir_exists   = os.path.exists(dest_dir)
    dest_dir_writable = os.access(dest_dir, os.W_OK)
    access_filename = DDRLocalFile.access_file_name(os.path.splitext(src_path)[0],
                                               settings.ACCESS_FILE_APPEND,
                                               'jpg') # see DDRLocalFile.make_access_file
    dest_basename     = os.path.basename(access_filename)
    dest_path         = os.path.join(dest_dir, dest_basename)
    dest_path_exists  = os.path.exists(dest_path)
    s = []
    if src_exists:         s.append('ok')
    else:                  entity.files_log(0, 'Source file does not exist: {}'.format(src_path))
    if src_readable:       s.append('ok')
    else:                  entity.files_log(0, 'Source file not readable: {}'.format(src_path))
    if dest_dir_exists:    s.append('ok')
    else:                  entity.files_log(0, 'Destination directory does not exist: {}'.format(dest_dir))
    if dest_dir_writable:  s.append('ok')
    else:                  entity.files_log(0, 'Destination directory not writable: {}'.format(dest_dir))
    #if not dest_path_exists: s.append('ok')
    #else:                  entity.files_log(0, 'Destination file already exists!: {}'.format(dest_path))
    preparations = ','.join(s)
    
    # do, or do not
    src_dest_ok = False
    if preparations == 'ok,ok,ok,ok':  # ,ok
        entity.files_log(1, 'Source file exists; is readable.  Destination dir exists, is writable.')
        src_dest_ok = True
        
    access_file = None
    apath = None
    if f and src_dest_ok:
        # task: make access file
        entity.files_log(1, 'Making access file...')
        # NOTE: do this before entity_annex_add so don't have to lock/unlock
        status,result = DDRLocalFile.make_access_file(f.path_abs,
                                                 settings.ACCESS_FILE_APPEND,
                                                 settings.ACCESS_FILE_GEOMETRY,
                                                 settings.ACCESS_FILE_OPTIONS)
        if status:
            entity.files_log(0, 'status: %s' % status)
            entity.files_log(0, 'result: %s' % result)
            entity.files_log(0, 'access file FAIL: %s' % result)
            f.access_rel = None
        else:
            entity.files_log(1, 'status: %s' % status)
            entity.files_log(1, 'result: %s' % result)
            access_rel = result
            f.set_access(access_rel, entity)
            entity.files_log(1, 'access_rel: %s' % f.access_rel)
            entity.files_log(1, 'access_abs: %s' % f.access_abs)
    
    if f and src_dest_ok and f.access_rel:
        entity.files_log(1, 'Adding %s to entity...' % f)
        # We have to write entity.json again so that access file gets recorded there.
        entity.files_log(1, 'Writing %s' % entity.json_path)
        entity.dump_json()
        f.dump_json()
        entity.files_log(1, 'done')
        # file JSON
        try:
            entity.files_log(1, 'entity_update(%s, %s, %s, %s, %s)' % (
                git_name, git_mail,
                entity.parent_path, entity.id,
                f.json_path))
            exit,status = entity_update(
                git_name, git_mail,
                entity.parent_path, entity.id,
                [f.json_path,],
                agent=agent)
            entity.files_log(1, 'entity_update: exit: %s' % exit)
            entity.files_log(1, 'entity_update: status: %s' % status)
        except:
            # TODO would be nice to know why entity_annex_add failed
            entity.files_log(0, 'entity_update: ERROR')
        if f.access_rel:
            access_basename = os.path.basename(f.access_rel)
            entity.files_log(1, 'access file: %s' % access_basename)
            try:
                # entity.json gets written as part of this
                entity.files_log(1, 'entity_annex_add(%s, %s, %s, %s, %s)' % (
                    git_name, git_mail,
                    entity.parent_path,
                    entity.id, access_basename))
                exit,status = entity_annex_add(
                    git_name, git_mail,
                    entity.parent_path,
                    entity.id, access_basename,
                    agent=agent)
                entity.files_log(1, 'entity_annex_add: exit: %s' % exit)
                entity.files_log(1, 'entity_annex_add: status: %s' % status)
            except:
                # TODO would be nice to know why entity_annex_add failed
                entity.files_log(0, 'entity_annex_add: ERROR')
        
    entity.files_log(1, 'ddrlocal.webui.tasks.add_access: FINISHED')
    return f.__dict__



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
        collection.cache_refresh()

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



@task(base=CollectionSyncDebugTask, name='webui-collection-refresh')
def collection_refresh( collection_path ):
    """Regenerate inventory and annex data.
    
    @param collection_path: Absolute path to collection repo.
    @return collection_path: Absolute path to collection.
    """
    # update search index
    add_update('ddr', 'collection', os.path.join(collection_path, 'collection.json'))
    # refresh redis caches
    collection = Collection.from_json(collection_path)
    collection.cache_refresh()
    return collection_path



class InventoryOpDebugTask(Task):
    abstract = True
    
    def on_failure(self, exc, task_id, args, kwargs, whatsthis):
        pass
    
    def on_success(self, retval, task_id, args, kwargs):
        pass
    
    def after_return(self, status, retval, task_id, args, kwargs, cinfo):
        pass

@task(base=InventoryOpDebugTask, name='webui-inventory-clone')
def inventory_clone( path, label, repo, org, cid, level, git_name, git_mail ):
    """Clones a collection to the local store.
    
    Clone the collection.
    Add collection to local Store.
    Update Inventory.
    Sync Inventory.
    
    @param path: Absolute path to dir that contains the Organization and collection repos.
    @param label: Drive label for drive on which the Store resides.
    @param repo
    @param org
    @param cid
    @param level: What level of git-annex files to get.
    @param git_name: Username for use in changelog, git log
    @param git_mail: User email address for use in changelog, git log
    """
    logger.debug('inventory_clone(%s, %s, %s, %s, %s, %s, %s, %s)' % (path, label, repo, org, cid, level, git_name, git_mail))
    collection_id = '-'.join([repo, org, cid])
    organization_id = '-'.join([repo, org])
    collection_path = os.path.join(path, collection_id)
    organization_path = os.path.join(path, organization_id)
    logger.debug('collection_id: %s' % collection_id)
    logger.debug('organization_id: %s' % organization_id)
    logger.debug('collection_path: %s' % collection_path)
    logger.debug('organization_path: %s' % organization_path)
    # clone
    logger.debug('clone(%s, %s, %s, %s)' % (git_name, git_mail, collection_id, collection_path))
    status,message = clone(git_name, git_mail, collection_id, collection_path)
    logger.debug('status: %s' % status)
    logger.debug('message: %s' % message)
    # update inventory
    if not status:
        logger.debug('Updating inventory')
        repository = dvcs.repository(collection_path)
        uuid = repository.git.config('annex.uuid')
        collection = {'uuid':uuid, 'cid':collection_id, 'level':level}
        logger.debug('Adding collection: %s' % collection)
        inventory.add_collection(organization_path, label, [collection], git_name, git_mail)
        logger.debug('Syncing inventory')
        inventory.sync_organization(organization_path)
        logger.debug('Updating inventory DONE')
    logger.debug('inventory_clone(%s, %s, %s, %s, %s, %s, %s, %s)' % (path, label, repo, org, cid, level, git_name, git_mail))
    return collection_path

@task(base=InventoryOpDebugTask, name='webui-inventory-drop')
def inventory_drop( path, label, repo, org, cid, git_name, git_mail ):
    """Drops a collection from the local store.
    
    @param path: Absolute path to dir that contains the Organization and collection repos.
    @param label: Drive label for drive on which the Store resides.
    @param repo
    @param org
    @param cid
    @param git_name: Username for use in changelog, git log
    @param git_mail: User email address for use in changelog, git log
    """
    #logger.debug('inventory_drop(%s, %s, %s, %s, %s, %s, %s)' % (path, label, repo, org, cid, git_name, git_mail))
    #collection_id = '-'.join([repo, org, cid])
    #collection_path = os.path.join(path, collection_id)
    #organization_id = '-'.join([repo, org])
    #organization_path = os.path.join(path, organization_id)
    #logger.debug('collection_id: %s' % collection_id)
    #logger.debug('collection_path: %s' % collection_path)
    #logger.debug('organization_id: %s' % organization_id)
    #logger.debug('organization_path: %s' % organization_path)
    #collection_uuid = dvcs.repository(collection_path).git.config('annex.uuid')
    #logger.debug('collection_uuid: %s' % collection_uuid)
    ## remove collection repo from store
    #logger.debug('Removing collection from inventory store: %s' % collection)
    #remove_collection(organization_path, label, collection_uuid, git_name, git_mail)
    ## remove collection from local Store
    ## commit Inventory
    ## sync Inventory
    #logger.debug('Syncing inventory')
    #inventory.sync_organization(organization_path)
    #logger.debug('Updating inventory DONE')
    return 'NOT IMPLEMENTED YET'



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
            try:
                msg = template.format(**task)
                task['message'] = msg
            except:
                if not task.get('message', None):
                    task['message'] = template
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
