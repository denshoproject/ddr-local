from datetime import datetime
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

from ddrlocal.models import DDRLocalEntity, DDRFile, hash

from DDR.commands import entity_annex_add



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
}



class DebugTask(Task):
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
        entity.files_log(1, 'DONE\n')


@task(base=DebugTask, name='entity-add-file')
def entity_add_file( git_name, git_mail, entity, src_path, role, sort, label='' ):
    """
    @param entity: DDRLocalEntity
    @param src_path: Absolute path to an uploadable file.
    @param role: Keyword of a file role.
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    """
    file_ = add_file(git_name, git_mail, entity, src_path, role, sort, label)
    return file_


def add_file( git_name, git_mail, entity, src_path, role, sort, label='' ):
    """Add file to entity
    
    This method breaks out of OOP and manipulates entity.json directly.
    Thus it needs to lock to prevent other edits while it does its thing.
    Writes a log to ${entity}/addfile.log, formatted in pseudo-TAP.
    This log is returned along with a DDRFile object.
    
    @param entity: DDRLocalEntity
    @param src_path: Absolute path to an uploadable file.
    @param role: Keyword of a file role.
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    @return file_ DDRFile object
    """
    f = None
                
    entity.files_log(1, 'ddrlocal.webui.tasks.add_file: START')
    entity.files_log(1, 'entity: %s' % entity.id)
    entity.files_log(1, 'src: %s' % src_path)
    entity.files_log(1, 'role: %s' % role)
    entity.files_log(1, 'sort: %s' % sort)
    entity.files_log(1, 'label: %s' % label)
    
    src_basename      = os.path.basename(src_path)
    src_exists        = os.path.exists(src_path)
    src_readable      = os.access(src_path, os.R_OK)
    if not os.path.exists(entity.files_path):
        os.mkdir(entity.files_path)
    dest_dir          = entity.files_path
    dest_dir_exists   = os.path.exists(dest_dir)
    dest_dir_writable = os.access(dest_dir, os.W_OK)
    dest_basename     = DDRFile.file_name(entity, src_path)
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
        
        f = DDRFile(entity=entity)
        f.role = role
        f.sort = sort
        f.label = label
        f.basename_orig = src_basename
        entity.files_log(1, 'Original filename: %s' % f.basename_orig)
        
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
            f.xmp = DDRFile.extract_xmp(src_path)
            if f.xmp:
                entity.files_log(1, 'got some XMP')
            else:
                entity.files_log(1, 'no XMP data')
        except:
            entity.files_log(0, 'XMP extract FAIL')
        
        # task: copy
        entity.files_log(1, 'Copying...')
        try:
            shutil.copy(src_path, dest_path)
        except:
            entity.files_log(0, 'copy FAIL')
        if os.path.exists(dest_path):
            cp_successful = True
            f.set_path(dest_path, entity=entity)
            entity.files_log(1, 'copied: %s' % f.path)
    
    thumbnail = None
    if f and cp_successful:
        # task: make thumbnail
        entity.files_log(1, 'Thumbnailing...')
        # NOTE: do this before entity_annex_add so don't have to lock/unlock
        try:
            thumbnail = f.make_thumbnail('500x500')
        except:
            entity.files_log(0, 'thumbnail FAIL')
        f.thumb = -1
        if thumbnail and hasattr(thumbnail, 'name') and thumbnail.name:
            entity.files_log(1, 'thumbnail.name: %s' % thumbnail.name)
            if thumbnail.name.find(settings.MEDIA_ROOT) == -1:
                tpath = os.path.join(settings.MEDIA_ROOT, thumbnail.name)
            else:
                tpath = thumbnail.name
            entity.files_log(1, 'tpath: %s' % tpath)
            if os.path.exists(tpath):
                if os.path.getsize(tpath):
                    f.thumb = 1
                    entity.files_log(1, 'thumbnail: ok')
                else:
                    f.thumb = 0
                    entity.files_log(0, 'thumbnail present but not valid (zero length?)')
                    entity.files_log(0, 'removing %s' % tpath)
                    os.remove(tpath)
                    if os.path.exists(tpath):
                        entity.files_log(0, 'could not remove!')
                    else:
                        entity.files_log(1, 'removed')
            else:
                f.thumb = 0
                entity.files_log(0, 'thumbnail not generated')
        entity.files_log(1, 'f.thumb: %s' % f.thumb)
        
    if f and cp_successful:
        # TODO task: make access copy
        entity.files_log(1, 'TODO access copy')
    
    if f and cp_successful:
        entity.files_log(1, 'Adding %s to entity...' % f)
        entity.files.append(f)
        entity.files_log(1, 'entity.files: %s' % entity.files)
        entity.files_log(1, 'Writing %s' % entity.json_path)
        entity.dump_json()
        entity.files_log(1, 'done')
        try:
            entity.files_log(1, 'entity_annex_add(%s, %s, %s, %s, %s)' % (
                git_name, git_mail,
                entity.parent_path,
                entity.id, dest_basename))
            exit,status = entity_annex_add(
                git_name, git_mail,
                entity.parent_path,
                entity.id, dest_basename)
            entity.files_log(1, 'entity_annex_add: exit: %s' % exit)
            entity.files_log(1, 'entity_annex_add: status: %s' % status)
        except:
            entity.files_log(0, 'entity_annex_add: ERROR')
        
    entity.files_log(1, 'ddrlocal.webui.tasks.add_file: FINISHED')
    return f.__dict__



def session_tasks( request ):
    """Gets task statuses from Celery API, appends to task dicts from session.
    
    @param request: A Django request object
    @return tasks: a dict with task_id for key
    """
    tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # add entity URLs
    for task_id in tasks.keys():
        task = tasks.get(task_id, None)
        if task:
            repo,org,cid,eid = task['entity_id'].split('-')
            task['entity_url'] = reverse('webui-entity', args=[repo,org,cid,eid])
    # get status, retval from celery
    for task_id in tasks.keys():
        url = 'http://127.0.0.1/%s' % reverse('celery-task_status', args=[task_id])
        r = requests.get(url)
        try:
            data = r.json()
            task = data['task']
        except:
            task = None
        if task:
            ctask = tasks[task['id']]
            ctask['status'] = task.get('status', None)
            ctask['result'] = task.get('result', None)
            if ctask['result']:
                url = reverse('webui-file', args=[ctask['result']['repo'],
                                                  ctask['result']['org'],
                                                  ctask['result']['cid'],
                                                  ctask['result']['eid'],
                                                  ctask['result']['sha1'],])
                ctask['file_url'] = url
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
    # can dismiss or not
    for task_id in tasks.keys():
        task = tasks[task_id]
        if task.get('status', None):
            task['dismissable'] = (task['status'] in TASK_STATUSES_DISMISSABLE)
    # done
    return tasks

def session_tasks_list( request ):
    """session_tasks as a list, sorted in reverse chronological order.
    
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
