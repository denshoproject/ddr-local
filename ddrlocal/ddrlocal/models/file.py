import os

from django.core.urlresolvers import reverse


FILEMETA_BLANK = {'sha1':None,
                  'status':'',
                  'public':0,
                  'sort':-1,
                  'label':'',
                  'exif':'',}


class DDRFile( object ):
    # files
    path = None
    basename = None
    size = None
    sha1 = None
    sha256 = None
    md5 = None
    # filemeta
    status = None
    public = None
    sort = None
    role = None
    label = None
    exif = None
    #
    src = None
    repo = None
    org = None
    cid = None
    eid = None
    
    def __init__(self, *args, **kwargs):
        if kwargs.get('file', None):
            self.sha1 = kwargs['file'].get('sha1', None)
            self.path = kwargs['file'].get('path', None)
            self.size = kwargs['file'].get('size', None)
            self.sha256 = kwargs['file'].get('sha256', None)
            self.md5 = kwargs['file'].get('md5', None)
        if self.path:
            self.basename = os.path.basename(self.path)
        if kwargs.get('meta', None):
            self.status = kwargs['meta'].get('status', None)
            self.public = kwargs['meta'].get('public', None)
            self.sort = kwargs['meta'].get('sort', None)
            self.role = kwargs['meta'].get('role', None)
            self.label = kwargs['meta'].get('label', None)
            self.exif = kwargs['meta'].get('exif', None)
        if kwargs.get('entity', None):
            self.repo = kwargs['entity'].repo
            self.org = kwargs['entity'].org
            self.cid = kwargs['entity'].cid
            self.eid = kwargs['entity'].eid
            self.src = os.path.join('base', kwargs['entity'].path_rel, self.path)
    
    def dict( self ):
        return self.__dict__

    @staticmethod
    def filemeta_blank():
        return FILEMETA_BLANK
    
    def url( self ):
        return reverse('webui-file', args=[self.repo, self.org, self.cid, self.eid, self.sha1[:10]])
