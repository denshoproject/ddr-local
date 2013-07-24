from datetime import datetime
import os
import shutil

from celery import task

from django.contrib import messages

from ddrlocal.models.entity import DDRLocalEntity
from ddrlocal.models.file import DDRFile, hash

from DDR.commands import entity_annex_add


@task()
def add(x, y):
    return x + y

@task(name='entity-add-file')
def entity_add_file( git_name, git_mail, entity, src_path, role, sort, label='' ):
    """
    @param entity: DDRLocalEntity
    @param src_path: Absolute path to an uploadable file.
    @param role: Keyword of a file role.
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    """
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
    
    def addfile_log( entity ):
        return os.path.join(entity.path, 'addfile.log')
    lf = addfile_log(entity)
    
    def log(logfile, ok, msg):
        if ok: ok = 'ok'
        else:  ok = 'not ok'
        entry = '[{}] {} - {}\n'.format(datetime.now().isoformat('T'), ok, msg)
        with open(lf, 'a') as f:
            f.write(entry)
            
    log(lf, 1, 'START')
    log(lf, 1, 'copying %s' % src_path)
    entity.lock()
    
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
            cp_successful = False
            if os.path.exists(dest_path):
                cp_successful = True
                f.set_path(dest_path, entity=entity)
                log(lf, 1, 'copy success: %s' % f.path)
        except:
            log(lf, 0, 'could not copy!')
        
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
        
        # TODO task: make access copy
        log(lf, 1, 'TODO access copy')
        
        entity.files.append(f)
        
        # entity_annex_add
        log(lf, 1, 'TODO entity_annex_add')
        exit,status = entity_annex_add(git_name, git_mail,
                                       entity.parent_path,
                                       entity.id, dest_basename)
        log(lf, 1, 'exit: %s' % exit)
        log(lf, 1, 'status: %s' % status)
        
    entity.unlock()
    log(lf, 1, 'FINISHED\n')
    
    logtxt = ''
    with open(lf, 'r') as l:
        logtxt = l.read()
    return f,logtxt
