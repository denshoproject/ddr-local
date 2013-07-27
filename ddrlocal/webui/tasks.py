from datetime import datetime
import os
import shutil

from celery import task
from celery import Task
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from django.contrib import messages

from ddrlocal.models.entity import DDRLocalEntity
from ddrlocal.models.file import DDRFile, hash

from DDR.commands import entity_annex_add


def addfile_log( entity ):
    return os.path.join(entity.path, 'addfile.log')

def log(logfile, ok, msg):
    if ok: ok = 'ok'
    else:  ok = 'not ok'
    entry = '[{}] {} - {}\n'.format(datetime.now().isoformat('T'), ok, msg)
    with open(logfile, 'a') as f:
        f.write(entry)


class DebugTask(Task):
    abstract = True

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        print('AFTER_RETURN')
        print('task_id %s' % task_id)
        print('status %s' % status)
        #print('retval %s' % retval)
        entity = args[2]
        src_path = args[3]
        print('entity.id %s' % entity.id)
        print('entity.path %s' % entity.path)
        print('src_path %s' % src_path)
        print('kwargs: %s' % kwargs.keys())
        entity.unlock(task_id)
        
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        print('ON_FAILURE')
        print('task_id %s' % task_id)
        print('exc %s' % exc)
        entity = args[2]
        src_path = args[3]
        print('entity.id %s' % entity.id)
        print('entity.path %s' % entity.path)
        print('src_path %s' % src_path)
        print('einfo %s' % einfo)
    
    def on_success(self, retval, task_id, args, kwargs):
        print('ON_SUCCESS')
        print('task_id %s' % task_id)
        entity = args[2]
        src_path = args[3]
        print('entity.id %s' % entity.id)
        print('entity.path %s' % entity.path)
        print('src_path %s' % src_path)

@task(base=DebugTask, name='entity-add-file')
def entity_add_file( git_name, git_mail, entity, src_path, role, sort, label='' ):
    """
    @param entity: DDRLocalEntity
    @param src_path: Absolute path to an uploadable file.
    @param role: Keyword of a file role.
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    """
    lf = addfile_log(entity)
    with open(lf, 'a') as f:
        f.write('LOCKING ENTITY')
    with open(lf, 'a') as f:
        f.write('LOCKED')
    file_ = None
    log = 'unknown error'
    file_,log = add_file(git_name, git_mail, entity, src_path, role, sort, label)
    return log


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
    @return file_,log Tuple consisting of a DDRFile object and log text.
    """
    f = None
    
    lf = addfile_log(entity)
                
    log(lf, 1, 'START')
    log(lf, 1, 'ENTITY: %s' % entity.id)
    log(lf, 1, 'ADDING: %s' % src_path)
    
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
    else:                  log(lf, 0, 'Source file does not exist: {}'.format(src_path))
    if src_readable:       s.append('ok')
    else:                  log(lf, 0, 'Source file not readable: {}'.format(src_path))
    if dest_dir_exists:    s.append('ok')
    else:                  log(lf, 0, 'Destination directory does not exist: {}'.format(dest_dir))
    if dest_dir_writable:  s.append('ok')
    else:                  log(lf, 0, 'Destination directory not writable: {}'.format(dest_dir))
    #if not dest_path_exists: s.append('ok')
    #else:                  log(lf, 0, 'Destination file already exists!: {}'.format(dest_path))
    preparations = ','.join(s)
    
    # do, or do not
    cp_successful = False
    if preparations == 'ok,ok,ok,ok':  # ,ok
        log(lf, 1, 'Proceeding with copy.')
        
        f = DDRFile(entity=entity)
        f.role = role
        f.sort = sort
        f.label = label
        
        # original filename
        f.basename_orig = src_basename
        log(lf, 1, 'original filename: %s' % f.basename_orig)
        
        # task: get SHA1 checksum (links entity.filemeta entity.files records
        try:
            f.sha1   = hash(src_path, 'sha1')
            log(lf, 1, 'sha1: %s' % f.sha1)
        except:
            log(lf, 0, 'error getting sha1')
        try:
            f.md5    = hash(src_path, 'md5')
            log(lf, 1, 'md5: %s' % f.md5)
        except:
            log(lf, 0, 'error getting md5')
        try:
            f.sha256 = hash(src_path, 'sha256')
            log(lf, 1, 'sha256: %s' % f.sha256)
        except:
            log(lf, 0, 'error getting sha256')
        
        # task: extract_xmp
        try:
            f.xmp = DDRFile.extract_xmp(src_path)
            log(lf, 1, 'XMP extracted')
        except:
            log(lf, 0, 'could not extract XMP')
        
        # task: copy
        try:
            log(lf, 1, 'copy start')
            shutil.copy(src_path, dest_path)
            log(lf, 1, 'copy end')
        except:
            log(lf, 0, 'could not copy!')
        if os.path.exists(dest_path):
            cp_successful = True
            f.set_path(dest_path, entity=entity)
            log(lf, 1, 'copy success: %s' % f.path)
    
    if f and cp_successful:
        # task: make thumbnail
        # NOTE: do this before entity_annex_add so don't have to lock/unlock
        try:
            thumbnail = f.make_thumbnail('500x500')
        except:
            thumbnail = None
            log(lf, 0, 'could not make thumbnail!')
        if thumbnail:
            f.thumb = 1
        else:
            f.thumb = 0
        log(lf, 1, 'thumbnail attempted: %s' % f.thumb)
        if thumbnail and hasattr(thumbnail, 'name') and thumbnail.name:
            log(lf, 1, 'thumbnail: %s' % thumbnail.name)
        
    if f and cp_successful:
        # TODO task: make access copy
        log(lf, 1, 'TODO access copy')
    
    if f and cp_successful:
        entity.files.append(f)
        try:
            log(lf, 1, 'entity_annex_add: start')
            exit,status = entity_annex_add(git_name, git_mail,
                                           entity.parent_path,
                                           entity.id, dest_basename)
            log(lf, 1, 'entity_annex_add: exit: %s' % exit)
            log(lf, 1, 'entity_annex_add: status: %s' % status)
        except:
            log(lf, 0, 'entity_annex_add: ERROR')
        
    log(lf, 1, 'FINISHED\n')
    
    logtxt = ''
    with open(lf, 'r') as l:
        logtxt = l.read()
    return f,logtxt
