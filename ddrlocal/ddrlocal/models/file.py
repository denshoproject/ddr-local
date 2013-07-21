import hashlib
import os

from django.core.urlresolvers import reverse



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
        xmp = None
        if os.path.exists(path):
            import libxmp
            xmp = libxmp.file_to_dict(path)
        return xmp
    
    def make_thumbnail( self ):
        pass
    
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
