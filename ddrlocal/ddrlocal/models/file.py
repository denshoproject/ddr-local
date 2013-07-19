import hashlib
import os

from django.core.urlresolvers import reverse


FILEMETA_BLANK = {'sha1':None,
                  'basename_orig':'',
                  'status':'',
                  'public':0,
                  'sort':-1,
                  'label':'',
                  'xmp':'',
                  'thumb':-1,
                  'log':[],}


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
    log = FILEMETA_BLANK['log']
    # entity
    src = None
    repo = None
    org = None
    cid = None
    eid = None
    
    def __init__(self, *args, **kwargs):
        if kwargs.get('path',None):
            self.path = kwargs['path']
        if kwargs.get('entity',None):
            self.repo = kwargs['entity'].repo
            self.org = kwargs['entity'].org
            self.cid = kwargs['entity'].cid
            self.eid = kwargs['entity'].eid
        if self.path:
            self.basename = os.path.basename(self.path)
        if self.path and kwargs.get('entity',None):
            self.src = os.path.join('base', kwargs['entity'].path_rel, self.path)
        
    
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
        f.sha1   = phile.get('sha1',None)
        f.sha256 = phile.get('sha256',None)
        f.md5    = phile.get('md5',None)
        # filemeta
        f.basename_orig = meta.get('basename_orig', FILEMETA_BLANK['basename_orig'])
        f.status = meta.get('status', FILEMETA_BLANK['status'])
        f.public = meta.get('public', FILEMETA_BLANK['public'])
        f.sort   = meta.get('sort',   FILEMETA_BLANK['sort'])
        f.role   = meta.get('role',   None)
        f.label  = meta.get('label',  FILEMETA_BLANK['label'])
        f.xmp   = meta.get('xmp',   FILEMETA_BLANK['xmp'])
        f.thumb  = meta.get('thumb',  FILEMETA_BLANK['thumb'])
        f.log    = meta.get('log',    FILEMETA_BLANK['log'])
        if f.path:
            f.basename = os.path.basename(f.path)
            f.src = os.path.join('base', entity.path_rel, f.path)
        return f
    
    def dict( self ):
        return self.__dict__
    
    @staticmethod
    def file_name( entity, path ):
        """Generate a new name for the specified file
        
        rename files to standard names on ingest:
        %{repo}-%{org}-%{cid}-%{eid}-%{sha1}.%{ext}
        example: ddr-testing-56-101-fb73f9de29.jpg
        """
        def hash(path):
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
        if os.path.exists and os.access(path, os.R_OK):
            ext = os.path.splitext(path)[1]
            sha1 = hash(path)
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
