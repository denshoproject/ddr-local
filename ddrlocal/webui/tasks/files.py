from datetime import datetime
import os

from elasticsearch.exceptions import ConnectionError, RequestError

from celery import task
from celery import Task
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from django.conf import settings

from DDR import converters
from DDR.ingest import addfile_logger

from webui import docstore
from webui import gitstatus
from webui.models import Collection, Entity, File
from webui.identifier import Identifier
from webui.tasks import dvcs as dvcs_tasks


# ----------------------------------------------------------------------

TASK_FILE_ADD_LOCAL_NAME = 'webui-file-new-local'
TASK_FILE_ADD_EXTERNAL_NAME = 'webui-file-new-external'
TASK_FILE_ADD_ACCESS_NAME = 'webui-file-new-access'

def add_local(request, form_data, entity, role, src_path, git_name, git_mail):
    collection = entity.collection()
    # start tasks
    result = file_add_local.apply_async(
        (entity.path, src_path, role, form_data, git_name, git_mail),
        countdown=2
    )
    log = addfile_logger(entity.identifier)
    log.ok('START %s' % TASK_FILE_ADD_LOCAL_NAME)
    log.ok('task_id %s' % result.task_id)
    log.ok('ddrlocal.webui.file.new')
    log.ok('Locking %s' % collection.id)
    # lock collection
    lockstatus = collection.lock(result.task_id)
    if lockstatus == 'ok':
        log.ok('locked')
    else:
        log.not_ok(lockstatus)
    # add celery task_id to session
    celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
    celery_tasks[result.task_id] = {
        'task_id': result.task_id,
        'action': TASK_FILE_ADD_LOCAL_NAME,
        'filename': os.path.basename(src_path),
        'entity_id': entity.id,
        'start': converters.datetime_to_text(datetime.now(settings.TZ)),
    }
    request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks

def add_external(request, form_data, entity, file_role, git_name, git_mail):
    collection = entity.collection()
    idparts = file_role.identifier.idparts
    idparts['model'] = 'file'
    idparts['sha1'] = form_data['sha1']
    fi = Identifier(parts=idparts)
    basename_orig = form_data['basename_orig']
    data = {
        'id': fi.id,
        'external': 1,
        'role': idparts['role'],
        'basename_orig': basename_orig,
        'sha1': form_data['sha1'],
        'sha256': form_data['sha256'],
        'md5': form_data['md5'],
        'size': form_data['size'],
        'mimetype': form_data['mimetype'],
    }
    # start tasks
    result = file_add_external.apply_async(
        (entity.path, data, git_name, git_mail),
        countdown=2
    )
    log = addfile_logger(entity.identifier)
    log.ok('START %s' % TASK_FILE_ADD_EXTERNAL_NAME)
    log.ok('task_id %s' % result.task_id)
    log.ok('ddrlocal.webui.file.external')
    log.ok('Locking %s' % collection.id)
    # lock collection
    lockstatus = collection.lock(result.task_id)
    if lockstatus == 'ok':
        log.ok('locked')
    else:
        log.not_ok(lockstatus)
    # add celery task_id to session
    celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
    celery_tasks[result.task_id] = {
        'task_id': result.task_id,
        'action': TASK_FILE_ADD_EXTERNAL_NAME,
        'filename': os.path.basename(basename_orig),
        'entity_id': entity.id,
        'start': converters.datetime_to_text(datetime.now(settings.TZ)),
    }
    request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks

def add_access(request, form_data, entity, file_, git_name, git_mail):
    collection = entity.collection()
    src_path = form_data['path']
    # start tasks
    result = file_add_access.apply_async(
        (entity.path, file_.dict(), src_path, git_name, git_mail),
        countdown=2
    )
    log = addfile_logger(entity.identifier)
    log.ok('START %s' % TASK_FILE_ADD_LOCAL_NAME)
    log.ok('task_id %s' % result.task_id)
    log.ok('ddrlocal.webui.file.new_access')
    log.ok('Locking %s' % collection.id)
    # lock collection
    lockstatus = collection.lock(result.task_id)
    if lockstatus == 'ok':
        log.ok('locked')
    else:
        log.not_ok(lockstatus)
    # add celery task_id to session
    celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
    celery_tasks[result.task_id] = {
        'task_id': result.task_id,
        'action': TASK_FILE_ADD_ACCESS_NAME,
        'filename': os.path.basename(src_path),
        'file_url': file_.absolute_url(),
        'entity_id': entity.id,
        'start': converters.datetime_to_text(datetime.now(settings.TZ)),
    }
    request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks

class FileAddDebugTask(Task):
    abstract = True
        
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        entity_path = args[0]
        eid = Identifier(path=entity_path)
        log = addfile_logger(eid)
        log.not_ok('DDRTask.ON_FAILURE')
        log.not_ok('exc %s' % exc)
        log.not_ok('einfo %s' % einfo)
    
    def on_success(self, retval, task_id, args, kwargs):
        entity_path = args[0]
        eid = Identifier(path=entity_path)
        log = addfile_logger(eid)
        log.ok('DDRTask.ON_SUCCESS')
        log.ok('retval %s' % retval)
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        entity_path = args[0]
        entity = Entity.from_identifier(Identifier(path=entity_path))
        collection = entity.collection()
        log = addfile_logger(entity.identifier)
        log.ok('FileAddDebugTask.AFTER_RETURN')
        log.ok('task_id: %s' % task_id)
        log.ok('status: %s' % status)
        log.ok('Unlocking %s' % collection.id)
        lockstatus = collection.unlock(task_id)
        if lockstatus == 'ok':
            log.ok('unlocked')
        else:
            log.not_ok(lockstatus)
        log.ok('END task_id %s\n' % task_id)
        collection.cache_delete()
        gitstatus.update(settings.MEDIA_BASE, collection.path)
        gitstatus.unlock(settings.MEDIA_BASE, 'file-add-*')

@task(base=FileAddDebugTask, name=TASK_FILE_ADD_LOCAL_NAME)
def file_add_local(entity_path, src_path, role, data, git_name, git_mail):
    """
    @param entity_path: str
    @param src_path: Absolute path to an uploadable file.
    @param role: Keyword of a file role.
    @param data: Dict containing form data.
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    """
    gitstatus.lock(settings.MEDIA_BASE, 'file-add-*')
    # TODO move this code to webui.models.Entity or .File
    entity = Entity.from_identifier(Identifier(path=entity_path))
    file_,repo,log = entity.add_local_file(
        src_path, role, data,
        git_name, git_mail, agent=settings.AGENT
    )
    file_,repo,log = entity.add_file_commit(
        file_, repo, log,
        git_name, git_mail, agent=settings.AGENT
    )
    log.ok('Updating Elasticsearch')
    logger.debug('Updating Elasticsearch')
    if settings.DOCSTORE_ENABLED:
        try:
            result = file_.post_json()
            log.ok('| %s' % result)
        except ConnectionError as err:
            log.not_ok("ConnectionError: {0}".format(err))
        except RequestError as err:
            log.not_ok("RequestError: {0}".format(err))
    return {
        'id': file_.id,
        'status': 'ok'
    }

@task(base=FileAddDebugTask, name=TASK_FILE_ADD_EXTERNAL_NAME)
def file_add_external(entity_path, data, git_name, git_mail):
    """
    @param entity_path: str
    @param data: Dict containing form data.
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    """
    gitstatus.lock(settings.MEDIA_BASE, 'file-add-*')
    entity = Entity.from_identifier(Identifier(path=entity_path))
    file_,repo,log = entity.add_external_file(
        data,
        git_name, git_mail, agent=settings.AGENT
    )
    file_,repo,log = entity.add_file_commit(
        file_, repo, log,
        git_name, git_mail, agent=settings.AGENT
    )
    log.ok('Updating Elasticsearch')
    logger.debug('Updating Elasticsearch')
    if settings.DOCSTORE_ENABLED:
        try:
            result = file_.post_json()
            log.ok('| %s' % result)
        except ConnectionError as err:
            log.not_ok("ConnectionError: {0}".format(err))
        except RequestError as err:
            log.not_ok("RequestError: {0}".format(err))
    return {
        'id': file_.id,
        'status': 'ok'
    }

@task(base=FileAddDebugTask, name=TASK_FILE_ADD_ACCESS_NAME)
def file_add_access(entity_path, file_data, src_path, git_name, git_mail):
    """
    @param entity_path: str
    @param file_data: dict
    @param src_path: Absolute path to an uploadable file.
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    """
    gitstatus.lock(settings.MEDIA_BASE, 'file-add-*')
    entity = Entity.from_identifier(Identifier(path=entity_path))
    file_ = File.from_identifier(Identifier(id=file_data['id']))
    file_,repo,log,op = entity.add_access(
        file_, file_.path_abs,
        git_name, git_mail, agent=settings.AGENT
    )
    if op and (op == 'pass'):
        log.ok('Things are okay as they are.  Leaving them alone.')
        return file_.dict(json_safe=True)
    file_,repo,log = entity.add_file_commit(
        file_, repo, log,
        git_name, git_mail, agent=settings.AGENT
    )
    log.ok('Updating Elasticsearch')
    logger.debug('Updating Elasticsearch')
    if settings.DOCSTORE_ENABLED:
        try:
            file_.post_json()
        except ConnectionError as err:
            log.not_ok("ConnectionError: {0}".format(err))
        except RequestError as err:
            log.not_ok("RequestError: {0}".format(err))
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
    file_ = File.from_identifier(fidentifier)
    gitstatus.lock(settings.MEDIA_BASE, 'file_edit')
    
    try:
        exit,status,updated_files = file_.save(
            git_name, git_mail, form_data
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
    file_ = File.from_identifier(Identifier(file_id))

    # TODO move this code to webui.models.File.delete
    exit,status,rm_files,updated_files = file_.delete(
        git_name, git_mail, agent
    )
    logger.debug('delete from search index')
    if settings.DOCSTORE_ENABLED:
        ds = docstore.Docstore()
        try:
            ds.delete(file_.id)
        except ConnectionError as err:
            logger.error("ConnectionError: {0}".format(err))
        except RequestError as err:
            logger.error("RequestError: {0}".format(err))
    
    return exit,status,collection_path,file_basename


# ----------------------------------------------------------------------

def signature(request, parent_id, file_id, git_name, git_mail):
    # start tasks
    parent = Identifier(id=parent_id).object()
    if parent.identifier.model == 'collection':
        collection = parent
    else:
        collection = parent.collection()
    result = set_signature.apply_async(
        (parent_id, file_id, git_name, git_mail),
        countdown=2
    )
    # lock collection
    lockstatus = collection.lock(result.task_id)
    # add celery task_id to session
    celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
    celery_tasks[result.task_id] = {
        'task_id': result.task_id,
        'action': 'set-signature',
        'parent_id': parent_id,
        'parent_url': parent.absolute_url(),
        'file_id': file_id,
        'start': converters.datetime_to_text(datetime.now(settings.TZ)),}
    request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks

class FileSignatureTask(Task):
    abstract = True
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        logger.debug('FileSignatureTask.after_return(%s, %s, %s, %s, %s)' % (
            status, retval, task_id, args, kwargs
        ))
        parent_id = args[0]
        parent = Identifier(id=parent_id).object()
        if parent.identifier.model == 'collection':
            collection = parent
        else:
            collection = parent.collection()
        collection_path = collection.identifier.path_abs()
        lockstatus = collection.unlock(task_id)
        gitstatus.update(settings.MEDIA_BASE, collection_path)
        gitstatus.unlock(settings.MEDIA_BASE, 'set_signature')

@task(base=FileSignatureTask, name='set-signature')
def set_signature(parent_id, file_id, git_name, git_mail):
    """Set file_id as signature of specified parent.
    
    @param parent_id: str
    @param file_id: str
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    """
    logger.debug('tasks.files.set_signature(%s,%s,%s,%s)' % (
        parent_id, file_id, git_name, git_mail
    ))
    parent = Identifier(id=parent_id).object()
    file_ = Identifier(id=file_id).object()
    collection_path = file_.collection_path
    parent.signature_id = file_id
    gitstatus.lock(settings.MEDIA_BASE, 'set_signature')
    exit,status,updated_files = parent.save(
        git_name, git_mail,
        {}
    )
    dvcs_tasks.gitstatus_update.apply_async(
        (collection_path,),
        countdown=2
    )
    return status,parent_id,file_id
