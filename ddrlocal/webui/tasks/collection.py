from datetime import datetime
import os

from celery import shared_task
from celery import Task
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from django.conf import settings
from django.urls import reverse

from DDR import commands
from DDR import converters
from DDR import docstore
from DDR import dvcs
from DDR import idservice
from DDR import signatures
from DDR import util

from elastictools import search
from elastictools.docstore import DocstoreManager
from elastictools.docstore import ConnectionError, RequestError, TransportError
from webui import batch
from webui import csvio
from webui import gitstatus
from webui.models import Collection, INDEX_PREFIX
from webui.identifier import Identifier
from webui.tasks import dvcs as dvcs_tasks


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
@shared_task(base=CollectionCheckTask, name='webui.tasks.collection_check')
def check( collection_path ):
    if not os.path.exists(settings.MEDIA_BASE):
        raise Exception('base_dir does not exist: %s' % settings.MEDIA_BASE)
    paths = util.find_meta_files(
        collection_path, recursive=1,
        model=None, files_first=False, force_read=False
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

TASK_COLLECTION_NEW_NAME = 'collection-new'
TASK_COLLECTION_NEW_MANUAL_NAME = 'collection-new-manual'
TASK_COLLECTION_NEW_IDSERVICE_NAME = 'collection-new-idservice'

def new_manual(request, cidentifier):
    # start tasks
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    result = collection_new_manual.apply_async(
        (cidentifier.path_abs(), git_name, git_mail),
        countdown=2
    )
    # add celery task_id to session
    celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # IMPORTANT: 'action' *must* match a msg in webui.tasks.TASK_STATUS_MESSAGES.
    celery_tasks[result.task_id] = {
        'task_id': result.task_id,
        'action': TASK_COLLECTION_NEW_MANUAL_NAME,
        'collection_url': reverse('webui-detail', args=[cidentifier.id]),
        'collection_id': cidentifier.id,
        'start': converters.datetime_to_text(datetime.now(settings.TZ)),}
    request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks

def new_idservice(request, oidentifier, git_name, git_mail):
    # start tasks
    result = collection_new_idservice.apply_async((
        oidentifier.id,
        request.session['idservice_token'],
        git_name,
        git_mail
    ))
    celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # IMPORTANT: 'action' *must* match a msg in webui.tasks.TASK_STATUS_MESSAGES.
    celery_tasks[result.task_id] = {
        'task_id': result.task_id,
        'action': TASK_COLLECTION_NEW_IDSERVICE_NAME,
        'organization_id': oidentifier.id,
        'collection_url': 'UNKNOWN',
        'collection_id': 'UNKNOWN',
        'start': converters.datetime_to_text(datetime.now(settings.TZ)),}
    request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks

class CollectionNewTask(Task):
    abstract = True
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        logger.debug('CollectionNewTask.after_return(%s, %s, %s, %s, %s)' % (
            status, retval, task_id, args, kwargs
        ))
        collection_id = retval['collection_id']
        collection = Collection.from_identifier(Identifier(id=collection_id))
        lockstatus = collection.unlock(task_id)
        gitstatus.update(settings.MEDIA_BASE, collection.path)
        # locking uses common name
        gitstatus.unlock(settings.MEDIA_BASE, TASK_COLLECTION_NEW_NAME)

@shared_task(base=CollectionNewTask, name=TASK_COLLECTION_NEW_MANUAL_NAME)
def collection_new_manual(collection_path, git_name, git_mail):
    """The time-consuming parts of collection-new-manual.
    
    @param collection_path: str Absolute path to collection
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    """
    logger.debug('tasks.collection.new_manual(%s,%s,%s)' % (
        collection_path, git_name, git_mail
    ))
    cidentifier = Identifier(path=collection_path)
    # locking uses common name
    gitstatus.lock(settings.MEDIA_BASE, TASK_COLLECTION_NEW_NAME)
    
    # Create collection
    try:
        exit,status = Collection.create(cidentifier, git_name, git_mail)
    except ConnectionError as err:
        logger.error("ConnectionError: {0}".format(err))
        exit = 1; status = {'error': err}
    except RequestError as err:
        logger.error("RequestError: {0}".format(err))
        exit = 1; status = {'error': err}
    collection = Collection.from_identifier(cidentifier)
    
    # update search index
    try:
        collection.post_json()
    except ConnectionError:
        logger.error('Could not post to Elasticsearch.')
    # do whatever this is
    dvcs_tasks.gitstatus_update.apply_async(
        (collection_path,),
        countdown=2
    )
    return status,collection_path

@shared_task(base=CollectionNewTask, name=TASK_COLLECTION_NEW_IDSERVICE_NAME)
def collection_new_idservice(organization_id, idservice_token, git_name, git_mail):
    """The time-consuming parts of collection-new-idservice.
    
    @param organization_id: str
    @param idservice_token: str
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    """
    logger.debug('tasks.collection.new_manual(%s,%s,%s,%s)' % (
        organization_id, idservice_token, git_name, git_mail
    ))
    oidentifier = Identifier(id=organization_id)
    # locking uses common name
    gitstatus.lock(settings.MEDIA_BASE, TASK_COLLECTION_NEW_NAME)

    ic = idservice.IDServiceClient()
    # resume session
    auth_status,auth_reason = ic.resume(idservice_token)
    if auth_status not in [200,201]:
        raise Exception('Could not authorize with ID service: {} {}' % (
            auth_status,auth_reason,
        ))
    # get new collection ID
    http_status,http_reason,collection_id = ic.next_object_id(
        oidentifier,
        'collection',
        register=True,
    )
    if http_status not in [200,201]:
        raise Exception('Could not get next %s id for %s: %s %s' % (
            'collection', organization_id, http_status, http_reason
        ))
    # Create collection
    cidentifier = Identifier(id=collection_id, base_path=settings.MEDIA_BASE)
    try:
        exit,status = Collection.create(cidentifier, git_name, git_mail)
    except ConnectionError as err:
        logger.error("ConnectionError: {0}".format(err))
        exit = 1; status = {'error': err}
    except RequestError as err:
        logger.error("RequestError: {0}".format(err))
        exit = 1; status = {'error': err}
    except OSError as err:
        logger.error("OSError: {0}".format(err))
        exit = 1; status = {'error': err}
    collection = Collection.from_identifier(cidentifier)
    
    # update search index
    try:
        collection.post_json()
    except ConnectionError:
        logger.error('Could not post to Elasticsearch.')
    # do whatever this is
    dvcs_tasks.gitstatus_update.apply_async(
        (collection.path,),
        countdown=2
    )
    return {
        'status':status,
        'collection_id': collection.id,
        'collection_url': reverse('webui-detail', args=[cidentifier.id]),
    }


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
        'action': 'collection-edit',
        'collection_url': collection.absolute_url(),
        'collection_id': collection.id,
        'start': converters.datetime_to_text(datetime.now(settings.TZ)),}
    request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks

class CollectionEditTask(Task):
    abstract = True
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        logger.debug('CollectionEditTask.after_return(%s, %s, %s, %s, %s)' % (
            status, retval, task_id, args, kwargs)
        )
        collection_path = args[0]
        collection = Collection.from_identifier(Identifier(path=collection_path))
        lockstatus = collection.unlock(task_id)
        gitstatus.update(settings.MEDIA_BASE, collection.path)
        gitstatus.unlock(settings.MEDIA_BASE, 'collection_edit')

@shared_task(base=CollectionEditTask, name='collection-edit')
def save(collection_path, cleaned_data, git_name, git_mail):
    """The time-consuming parts of collection-edit.
    
    @param collection_path: str Absolute path to collection
    @param cleaned_data: dict form.cleaned_data
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    """
    logger.debug('tasks.collection.save(%s,%s,%s)' % (
        git_name, git_mail, collection_path))
    
    collection = Collection.from_identifier(Identifier(path=collection_path))
    gitstatus.lock(settings.MEDIA_BASE, 'collection_edit')
    
    try:
        exit,status,updated_files = collection.save(
            git_name, git_mail, cleaned_data
        )
    except ConnectionError as err:
        logger.error("ConnectionError: {0}".format(err))
        exit = 1; status = {'error': err}
    except RequestError as err:
        logger.error("RequestError: {0}".format(err))
        exit = 1; status = {'error': err}
    
    dvcs_tasks.gitstatus_update.apply_async(
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

@shared_task(base=CollectionSyncDebugTask, name='collection-sync')
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

@shared_task(base=CollectionSignaturesDebugTask, name='collection-signatures')
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

def csv_export(request, collection, model):
    result = csv_export_model.apply_async(
        (collection.path, model),
        countdown=2
    )
    # add celery task_id to session
    celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
    task = {
        'task_id': result.task_id,
        'action': 'csv-export-model',
        'collection_id': collection.id,
        'collection_url': collection.absolute_url(),
        'things': csvio.models(model),
        'file_name': csvio.csv_filename(collection, model),
        'file_url': csvio.csv_url(collection, model),
        'start': converters.datetime_to_text(datetime.now(settings.TZ)),
    }
    celery_tasks[result.task_id] = task
    request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks

class CSVExportDebugTask(Task):
    abstract = True
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        pass
    def on_success(self, retval, task_id, args, kwargs):
        pass
    def after_return(self, status, retval, task_id, args, kwargs, cinfo):
        pass

@shared_task(base=CSVExportDebugTask, name='webui-csv-export-model')
def csv_export_model(collection_path, model):
    """Export collection {model} metadata to CSV file.
    
    @return collection_path: Absolute path to collection.
    @return model: 'entity' or 'file'.
    """
    return str(csvio.export_to_csv(
        Collection.from_identifier(Identifier(path=collection_path)),
        model,
        logger
    ))


# ----------------------------------------------------------------------

def csv_import(request, collection, model, csv_path):
    log_path = batch.get_log_path(csv_path)
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    result = csv_import_model.apply_async(
        (collection.path, model, str(csv_path), git_name, git_mail),
        countdown=2
    )
    # add celery task_id to session
    celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
    task = {
        'task_id': result.task_id,
        'action': f'csv-import-{model}',
        'collection_id': collection.id,
        'collection_url': collection.absolute_url(),
        'model': model,
        'csv_path': str(csv_path),
        'csv_file': str(csv_path.name),
        'log_path': str(log_path),
        'log_url': batch.get_log_url(log_path),
        'start': converters.datetime_to_text(datetime.now(settings.TZ)),
    }
    celery_tasks[result.task_id] = task
    request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks

class CSVImportTask(Task):
    abstract = True
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        collection_path = args[0]
        model = args[1]
        csv_path = args[2]
        git_name = args[3]
        git_mail = args[4]
        log_path = batch.get_log_path(csv_path)
        log = util.FileLogger(log_path=log_path)
        log.error('Import failed -- rolling back')
        dvcs.rollback(dvcs.repository(collection_path, git_name, git_mail), log)
        log.blank()
        log.blank()
    
    def on_success(self, retval, task_id, args, kwargs):
        pass
    
    def after_return(self, status, retval, task_id, args, kwargs, cinfo):
        logger.debug('CSVImportTask.after_return(%s, %s, %s, %s, %s)' % (
            status, retval, task_id, args, kwargs)
        )
        collection_path = args[0]
        model = args[1]
        csv_path = args[2]
        git_name = args[3]
        git_mail = args[4]
        collection = Collection.from_identifier(Identifier(path=collection_path))
        lockstatus = collection.unlock(task_id)
        gitstatus.update(settings.MEDIA_BASE, collection.path)
        gitstatus.unlock(settings.MEDIA_BASE, 'csv_import')

@shared_task(base=CSVImportTask, name='webui-csv-import-model')
def csv_import_model(collection_path, model, csv_path, git_name, git_mail):
    """Import collection {model} metadata to CSV file.
    
    @return collection_path: Absolute path to collection.
    @return model: 'entity' or 'file'.
    """
    log_path = batch.get_log_path(csv_path)
    log = util.FileLogger(log_path=log_path)
    log.info(f'========================================================================')
    log.info(f'BEGIN BATCH {model.upper()} IMPORT')
    log.info(f'========================================================================')
    ci = Identifier(path=collection_path)
    collection = Collection.from_identifier(ci)
    
    rowds,errors = batch.load_csv_run_checks(collection, model, csv_path)
    if errors:
        raise Exception(
            'File import cancelled due to CSV validation errors. ' \
            'Please see import log.'
        )
    gitstatus.lock(settings.MEDIA_BASE, 'csv_import')
    imported = batch.Importer.import_files(
        csv_path=csv_path,
        rowds=rowds,
        cidentifier=ci,
        vocabs_url=settings.VOCABS_URL,
        git_name=git_name,
        git_mail=git_mail,
        agent='ddr-local',
        log_path=log_path,
    )
    commit = dvcs.commit(
        repo=dvcs.repository(collection_path, git_name, git_mail),
        msg=f'Batch file import\n\nCSV: {csv_path}',
        agent='ddr-local',
        log=log,
    )
    status,msg = batch.csv_update_signatures(
        collection, rowds, git_name, git_mail, agent='ddr-local', log=log
    )
    log.blank()
    log.blank()

    logger.debug('Updating Elasticsearch')
    if settings.DOCSTORE_ENABLED:
        try:
            collection.reindex()
        except ConnectionError:
            logger.error('Could not update search index')
    return collection_path,model,csv_path


# ----------------------------------------------------------------------

TASK_COLLECTION_REINDEX = 'collection-reindex'

def reindex(request, collection):
    # start tasks
    collection_path = collection.path
    result = collection_reindex.apply_async(
        (collection_path,),
        countdown=2
    )
    # add celery task_id to session
    celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
    celery_tasks[result.task_id] = {
        'task_id': result.task_id,
        'action': TASK_COLLECTION_REINDEX,
        'collection_id': collection.id,
        'collection_url': collection.absolute_url(),
        'start': converters.datetime_to_text(datetime.now(settings.TZ)),}
    request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks

class ReindexDebugTask(Task):
    abstract = True
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        pass
    
    def on_success(self, retval, task_id, args, kwargs):
        pass
    
    def after_return(self, status, retval, task_id, args, kwargs, cinfo):
        pass

@shared_task(base=ReindexDebugTask, name=TASK_COLLECTION_REINDEX)
def collection_reindex(collection_path):
    """Reindexes collection
    
    @param collection_path: Absolute path to collection repo.
    @return collection_path: Absolute path to collection.
    """
    logger.debug('tasks.collection.reindex({})'.format(collection_path))
    collection = Collection.from_identifier(Identifier(path=collection_path))
    if settings.DOCSTORE_ENABLED:
        # nice UI if Elasticsearch is down
        try:
            DocstoreManager(
                INDEX_PREFIX, settings.DOCSTORE_HOST, settings
            ).status()
        except TransportError:
            raise Exception(
                "<b>TransportError</b>: Cannot connect to search engine."
            )
        collection.reindex()
    else:
        raise Exception('Search engine disabled (DOCSTORE_ENABLED=False)')
    return collection_path
