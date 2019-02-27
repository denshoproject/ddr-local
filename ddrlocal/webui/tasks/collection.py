from datetime import datetime, timedelta
import os

from elasticsearch.exceptions import ConnectionError

from celery import task
from celery import Task
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from django.conf import settings

from webui import gitstatus
from webui.models import Collection, Entity, DDRFile
from webui.identifier import Identifier

from DDR import batch
from DDR import commands
from DDR import converters
from DDR import models
from DDR import signatures
from DDR import util

from .common import TASK_STATUSES, TASK_STATUSES_DISMISSABLE, TASK_STATUS_MESSAGES
from .common import DebugTask


# ----------------------------------------------------------------------

class CollectionCheckTask(Task):
    abstract = True
        
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        pass
    
    def on_success(self, retval, task_id, args, kwargs):
        pass
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        logger.debug('CollectionCheckTask.after_return(%s, %s, %s, %s, %s, %s)' % (status, retval, task_id, args, kwargs, einfo))
        gitstatus.log('CollectionCheckTask.after_return(%s, %s, %s, %s, %s, %s)' % (status, retval, task_id, args, kwargs, einfo))

@task(base=CollectionCheckTask, name='webui.tasks.collection_check')
def check( collection_path ):
    if not os.path.exists(settings.MEDIA_BASE):
        raise Exception('base_dir does not exist: %s' % settings.MEDIA_BASE)
    paths = util.find_meta_files(
        collection_path, recursive=1,
        model=None, files_first=False, force_read=False, testing=0
    )
    bad_files = util.validate_paths(paths)
    output = [
        'Checked %s files' % len(paths),
    ]
    if bad_files:
        for item in bad_files:
            n,path,err = item
            output.append(
                '%s/%s ERROR %s - %s' % (n, len(paths), path, err)
            )
    else:
        output.append('No bad files.')
    output.append('DONE')
    return '\n'.join(output)


# ----------------------------------------------------------------------

def edit(request, collection, cleaned_data, git_name, git_mail):
    # start tasks
    
    result = save.apply_async(
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
def save(collection_path, cleaned_data, git_name, git_mail):
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
def sync( git_name, git_mail, collection_path ):
    """Synchronizes collection repo with workbench server.
    
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    @param collection_path: Absolute path to collection repo.
    @return collection_path: Absolute path to collection.
    """
    gitstatus.lock(settings.MEDIA_BASE, 'collection_sync')
    ci = Identifier(path=collection_path)
    collection = Collection.from_identifier(ci)
    
    # TODO move this code to webui.models.Collection.sync
    exit,status = commands.sync(
        git_name, git_mail,
        collection
    )
    logger.debug('Updating Elasticsearch')
    if settings.DOCSTORE_ENABLED:
        try:
            collection.reindex()
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
def signatures(collection_path, git_name, git_mail):
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

    # TODO move this code to webui.models.Collection
    status,msg = signatures.commit_updates(
        collection,
        files_written,
        git_name, git_mail, agent='ddr-local'
    )
    logger.debug('DONE')
    logger.debug('Updating Elasticsearch')
    if settings.DOCSTORE_ENABLED:
        collection = Collection.from_identifier(Identifier(path=collection_path))
        try:
            collection.post_json()
        except ConnectionError:
            logger.error('Could not update search index')
    
    return collection_path


# ----------------------------------------------------------------------

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
