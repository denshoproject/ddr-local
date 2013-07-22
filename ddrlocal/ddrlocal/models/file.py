from datetime import datetime
import hashlib
import os
import shutil

import libxmp
from lxml import etree

from django.core.files import File
from django.core.urlresolvers import reverse

from sorl.thumbnail import default

from DDR.commands import entity_annex_add


FILE_KEYS = ['path', 
             'basename', 
             'size', 
             'role', 
             'sha1', 
             'sha256', 
             'md5',]
FILEMETA_BLANK = {'sha1':None,
                  'basename_orig':'',
                  'status':'',
                  'public':0,
                  'sort':-1,
                  'label':'',
                  'thumb':-1,
                  'xmp':'',}
FILEMETA_KEYS = FILEMETA_BLANK.keys()


def hash(path, algo='sha1'):
    if algo == 'sha256':
        h = hashlib.sha256()
    elif algo == 'md5':
        h = hashlib.md5()
    else:
        h = hashlib.sha1()
    block_size=1024
    f = open(path, 'rb')
    while True:
        data = f.read(block_size)
        if not data:
            break
        h.update(data)
    f.close()
    return h.hexdigest()


class DDRFile( object ):
    # files
    path = None
    basename = None
    size = None
    role = None
    sha1 = None
    sha256 = None
    md5 = None
    # filemeta
    basename_orig = FILEMETA_BLANK['basename_orig']
    status = FILEMETA_BLANK['status']
    public = FILEMETA_BLANK['public']
    sort = FILEMETA_BLANK['sort']
    label = FILEMETA_BLANK['label']
    xmp = FILEMETA_BLANK['xmp']
    thumb = FILEMETA_BLANK['thumb']
    # entity
    src = None
    repo = None
    org = None
    cid = None
    eid = None
    
    def __init__(self, *args, **kwargs):
        # files
        if kwargs.get('path',None) and kwargs.get('entity',None):
            self.set_path(kwargs['path'], kwargs['entity'])
        elif kwargs.get('path',None):
            self.set_path(kwargs['path'])
        # filemeta
        self.basename_orig = FILEMETA_BLANK['basename_orig']
        self.status = FILEMETA_BLANK['status']
        self.public = FILEMETA_BLANK['public']
        self.sort = FILEMETA_BLANK['sort']
        self.label = FILEMETA_BLANK['label']
        self.xmp = FILEMETA_BLANK['xmp']
        self.thumb = FILEMETA_BLANK['thumb']
        # entity
        if kwargs.get('entity',None):
            self.repo = kwargs['entity'].repo
            self.org = kwargs['entity'].org
            self.cid = kwargs['entity'].cid
            self.eid = kwargs['entity'].eid

    @staticmethod
    def from_entity(entity, phile, meta):
        f = DDRFile()
        # entity
        f.repo = entity.repo
        f.org = entity.org
        f.cid = entity.cid
        f.eid = entity.eid
        # files
        f.path   = phile.get('path',None)
        f.size   = phile.get('size',None)
        f.role   = phile.get('role',None)
        f.sha1   = phile.get('sha1',None)
        f.sha256 = phile.get('sha256',None)
        f.md5    = phile.get('md5',None)
        # filemeta
        f.basename_orig = meta.get('basename_orig', FILEMETA_BLANK['basename_orig'])
        f.status = meta.get('status', FILEMETA_BLANK['status'])
        f.public = meta.get('public', FILEMETA_BLANK['public'])
        f.sort   = meta.get('sort',   FILEMETA_BLANK['sort'])
        f.label  = meta.get('label',  FILEMETA_BLANK['label'])
        f.xmp   = meta.get('xmp',   FILEMETA_BLANK['xmp'])
        f.thumb  = meta.get('thumb',  FILEMETA_BLANK['thumb'])
        if f.path:
            f.basename = os.path.basename(f.path)
            f.src = os.path.join('base', entity.path_rel, f.path)
        return f
    
    def set_path( self, path, entity=None ):
        self.path = path
        self.size = os.path.getsize(self.path)
        self.basename = os.path.basename(self.path)
        if entity:
            self.src = os.path.join('base', entity.path_rel, self.path)
    
    def file( self ):
        """Simulates an entity['files'] dict used to construct file"""
        f = {}
        for key in FILE_KEYS:
            if hasattr(self, key):
                f[key] = getattr(self, key, None)
        return f
    
    def filemeta( self ):
        """Simulates an entity['filemeta'] dict used to construct file"""
        f = {}
        for key in FILEMETA_KEYS:
            if hasattr(self, key) and (key != 'sha1'):
                f[key] = getattr(self, key, None)
        return f
        
    def dict( self ):
        return self.__dict__
    
    @staticmethod
    def extract_xmp( path ):
        """Attempts to extract XMP data from a file, returns as dict.
        
        @return dict NOTE: this is not an XML file!
        """
        xmpfile = libxmp.files.XMPFiles()
        try:
            xmpfile.open_file(path, open_read=True)
            xmp = xmpfile.get_xmp()
        except:
            xmp = None
        if xmp:
            xml  = xmp.serialize_to_unicode()
            tree = etree.fromstring(xml)
            str = etree.tostring(tree, pretty_print=False).strip()
            while str.find('\n ') > -1:
                str = str.replace('\n ', '\n')
            str = str.replace('\n','')
            return str
        return None
    
    def make_thumbnail( self, geometry, options={} ):
        """Attempt to make thumbnail.
        
        See sorl.thumbnail.templatetags.thumbnail.ThumbnailNode.render 
        https://github.com/sorl/sorl-thumbnail/blob/master/sorl/thumbnail/templatetags/thumbnail.py
        
        from django.core.files import File
        from sorl.thumbnail import default
        from ddrlocal.models.entity import DDRLocalEntity
        entity = DDRLocalEntity.from_json('/var/www/media/base/ddr-testing-61/files/ddr-testing-61-3')
        ef = entity.files[0]
        with open(ef.path, 'r') as f:
            file_ = File(f)
         
        geometry = '200x200'
        thumbnail = default.backend.get_thumbnail(file_, geometry)
        """
        thumbnail = None
        if self.path:
            with open(self.path, 'r') as f:
                file_ = File(f)
            thumbnail = default.backend.get_thumbnail(file_, geometry)
        return thumbnail
    
    @staticmethod
    def file_name( entity, path ):
        """Generate a new name for the specified file
        
        rename files to standard names on ingest:
        %{repo}-%{org}-%{cid}-%{eid}-%{sha1}.%{ext}
        example: ddr-testing-56-101-fb73f9de29.jpg
        """
        if os.path.exists and os.access(path, os.R_OK):
            ext = os.path.splitext(path)[1]
            sha1 = hash(path, 'sha1')
            if sha1:
                base = '-'.join([
                    entity.repo, entity.org, entity.cid, entity.eid,
                    sha1[:10]
                ])
                name = '{}{}'.format(base, ext)
                return name
        return None
    
    @staticmethod
    def filemeta_blank():
        return FILEMETA_BLANK
    
    def url( self ):
        return reverse('webui-file', args=[self.repo, self.org, self.cid, self.eid, self.sha1[:10]])



def entity_add_file( entity, src_path, role, git_name, git_mail ):
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
    if not dest_path_exists: s.append('ok')
    else:                  log(lf, 0, 'Destination file already exists!: {}'.format(dest_path))
    preparations = ','.join(s)
    # do, or do not
    if preparations == 'ok,ok,ok,ok,ok':
        log(lf, 1, 'Proceeding with copy.')
        
        f = DDRFile(entity=entity)
        f.role = role
        
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
