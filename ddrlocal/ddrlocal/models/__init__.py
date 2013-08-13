from datetime import datetime, date
import hashlib
import json
import os
from StringIO import StringIO

import envoy
import libxmp
from lxml import etree
from sorl.thumbnail import default

from django.conf import settings
from django.core.files import File
from django.core.urlresolvers import reverse

from DDR.models import DDRCollection, DDREntity
from ddrlocal import VERSION, git_commit
from ddrlocal.models.collection import COLLECTION_FIELDS
from ddrlocal.models.entity import ENTITY_FIELDS



class DDRLocalCollection( DDRCollection ):
    """
    This subclass of Entity and DDREntity adds functions for reading and writing
    entity.json, and preparing/processing Django forms.
    """
    id = 'whatever'
    repo = None
    org = None
    cid = None

    def __init__(self, *args, **kwargs):
        super(DDRLocalCollection, self).__init__(*args, **kwargs)
        self.id = self.uid
        self.repo = self.id.split('-')[0]
        self.org = self.id.split('-')[1]
        self.cid = self.id.split('-')[2]
    
    def __repr__(self):
        return "<DDRLocalCollection %s>" % (self.id)
    
    def url( self ):
        return reverse('webui-collection', args=[self.repo, self.org, self.cid])
    
    @staticmethod
    def collection_path(request, repo, org, cid):
        return os.path.join(settings.MEDIA_BASE, '{}-{}-{}'.format(repo, org, cid))
    
    def _lockfile( self ):
        return os.path.join(self.path, 'lock')
     
    def lock( self, task_id ):
        """Writes lockfile to collection dir; complains if can't.
        
        Celery tasks don't seem to know their own task_id, and there don't
        appear to be any handlers that can be called just *before* a task
        is fired. so it appears to be impossible for a task to lock itself.
        
        This method should(?) be called immediately after starting the task:
        >> result = collection_sync.apply_async((args...), countdown=2)
        >> lock_status = collection.lock(result.task_id)

        @param task_id
        @returns 'ok' or 'locked'
        """
        path = self._lockfile()
        if os.path.exists(path):
            return 'locked'
        with open(self._lockfile(), 'w') as f:
            f.write(task_id)
        return 'ok'
     
    def unlock( self, task_id ):
        """Removes lockfile or complains if can't
        
        This method should be called by celery Task.after_return()
        See "Abstract classes" section of http://celery.readthedocs.org/en/latest/userguide/tasks.html#custom-task-classes
        
        @param task_id
        @returns 'ok', 'not locked', 'task_id miss', 'blocked'
        """
        path = self._lockfile()
        if not os.path.exists(path):
            return 'not locked'
        with open(path, 'r') as f:
            lockfile_task_id = f.read().strip()
        if lockfile_task_id and (lockfile_task_id != task_id):
            return 'task_id miss'
        os.remove(path)
        if os.path.exists(path):
            return 'blocked'
        return 'ok'
    
    def locked( self ):
        """Indicates whether collection is locked; if locked returns celery task_id.
        """
        path = self._lockfile()
        if os.path.exists(path):
            with open(path, 'r') as f:
                task_id = f.read().strip()
            return task_id
        return False
    
    @staticmethod
    def create(path):
        """Creates a new collection with the specified collection ID.
        @param path: Absolute path to collection; must end in valid DDR collection id.
        """
        collection = Collection(path)
        for f in COLLECTION_FIELDS:
            if hasattr(f, 'name') and hasattr(f, 'initial'):
                setattr(collection, f['name'], f['initial'])
        return collection
    
    def entities( self ):
        """Returns relative paths to entities."""
        entities = []
        if os.path.exists(self.files_path):
            for eid in os.listdir(self.files_path):
                path = os.path.join(self.files_path, eid)
                entity = DDRLocalEntity.from_json(path)
                for lv in entity.labels_values():
                    if lv['label'] == 'title':
                        entity.title = lv['value']
                entities.append(entity)
        return entities
    
    def labels_values(self):
        """Generic display
        """
        lv = []
        for f in COLLECTION_FIELDS:
            if hasattr(self, f['name']) and f.get('form',None):
                item = {'label': f['form']['label'],
                        'value': getattr(self, f['name'])}
                lv.append(item)
        return lv
    
    def form_data(self):
        """Prep data dict to pass into CollectionForm object.
        
        Certain fields may require special processing, which will be performed
        by the function specified in field['prep_func'].
        
        @returns data: dict object as used by Django Form object.
        """
        data = {}
        for f in COLLECTION_FIELDS:
            if hasattr(self, f['name']) and f.get('form',None):
                key = f['name']
                value = getattr(self, f['name'])
                # hand off special processing to function specified in COLLECTION_FIELDS
                if f.get('prep_func',None):
                    func = f['prep_func']
                    value = func(value)
                # end special processing
                data[key] = value
        return data
    
    def form_process(self, form):
        """Process cleaned_data coming from CollectionForm
        
        Certain fields may require special processing, which will be performed
        by the function specified in field['proc_func'].
        
        @param form
        """
        for f in COLLECTION_FIELDS:
            if hasattr(self, f['name']) and f.get('form',None):
                key = f['name']
                cleaned_data = form.cleaned_data[key]
                # hand off special processing to function specified in COLLECTION_FIELDS
                if f.get('proc_func',None):
                    func = f['proc_func']
                    cleaned_data = func(cleaned_data)
                # end special processing
                setattr(self, key, cleaned_data)
        # update lastmod
        self.lastmod = datetime.now()
    
    @staticmethod
    def from_json(collection_abs):
        collection = DDRLocalCollection(collection_abs)
        collection_uid = collection.id  # save this just in case
        collection.load_json(collection.json_path)
        if not collection.id:
            # id gets overwritten if collection.json is blank
            collection.id = collection_uid
        return collection
    
    def load_json(self, path):
        """Populate Collection data from .json file.
        @param path: Absolute path to collection directory
        """
        json_data = self.json().data
        for ff in COLLECTION_FIELDS:
            for f in json_data:
                if f.keys()[0] == ff['name']:
                    setattr(self, f.keys()[0], f.values()[0])
        # special cases
        if self.created:
            self.created = datetime.strptime(self.created, settings.DATETIME_FORMAT)
        else:
            self.created = datetime.now()
        if self.lastmod:
            self.lastmod = datetime.strptime(self.lastmod, settings.DATETIME_FORMAT)
        else:
            self.lastmod = datetime.now()
        # end special cases
        # Ensure that every field in COLLECTION_FIELDS is represented
        # even if not present in json_data.
        for ff in COLLECTION_FIELDS:
            if not hasattr(self, ff['name']):
                setattr(self, ff['name'], ff.get('default',None))
    
    def dump_json(self):
        """Dump Collection data to .json file.
        @param path: Absolute path to .json file.
        """
        collection = [{'application': 'https://github.com/densho/ddr-local.git',
                       'commit': git_commit(),
                       'release': VERSION,}]
        for ff in COLLECTION_FIELDS:
            item = {}
            key = ff['name']
            val = ''
            if hasattr(self, ff['name']):
                val = getattr(self, ff['name'])
                # special cases
                if key in ['created', 'lastmod']:
                    val = val.strftime(settings.DATETIME_FORMAT)
                elif key in ['digitize_date']:
                    val = val.strftime(settings.DATE_FORMAT)
                # end special cases
            item[key] = val
            collection.append(item)
        json_pretty = json.dumps(collection, indent=4, separators=(',', ': '))
        with open(self.json_path, 'w') as f:
            f.write(json_pretty)
    
    def dump_ead(self):
        """Dump Collection data to ead.xml file.
        """
        NAMESPACES = None
        tree = etree.fromstring(self.ead().xml)
        for f in COLLECTION_FIELDS:
            key = f['name']
            value = ''
            if hasattr(self, f['name']):
                value = getattr(self, f['name'])
                # hand off special processing to function specified in COLLECTION_FIELDS
                if f.get('ead_func',None):
                    func = f['ead_func']
                    tree = func(tree, NAMESPACES, f, value)
                # end special processing
        xml_pretty = etree.tostring(tree, pretty_print=True)
        with open(self.ead_path, 'w') as f:
            f.write(xml_pretty)



class DDRLocalEntity( DDREntity ):
    """
    This subclass of Entity and DDREntity adds functions for reading and writing
    entity.json, and preparing/processing Django forms.
    """
    id = 'whatever'
    repo = None
    org = None
    cid = None
    eid = None
    _files = []
    
    def __init__(self, *args, **kwargs):
        super(DDRLocalEntity, self).__init__(*args, **kwargs)
        self.id = self.uid
        self.repo = self.id.split('-')[0]
        self.org = self.id.split('-')[1]
        self.cid = self.id.split('-')[2]
        self.eid = self.id.split('-')[3]
        self._files = []
        self._filemeta = []
    
    def __repr__(self):
        return "<DDRLocalEntity %s>" % (self.id)
    
    def url( self ):
        return reverse('webui-entity', args=[self.repo, self.org, self.cid, self.eid])

    @staticmethod
    def entity_path(request, repo, org, cid, eid):
        collection_uid = '{}-{}-{}'.format(repo, org, cid)
        entity_uid     = '{}-{}-{}-{}'.format(repo, org, cid, eid)
        collection_abs = os.path.join(settings.MEDIA_BASE, collection_uid)
        entity_abs     = os.path.join(collection_abs,'files',entity_uid)
        return entity_abs
    
    def _lockfile( self ):
        return os.path.join(self.path, 'lock')
     
    def lock( self, task_id ):
        """Writes lockfile to entity dir; complains if can't.
        
        Celery tasks don't seem to know their own task_id, and there don't
        appear to be any handlers that can be called just *before* a task
        is fired. so it appears to be impossible for a task to lock itself.
        
        This method should(?) be called immediately after starting the task:
        >> result = entity_add_file.apply_async((args...), countdown=2)
        >> lock_status = entity.lock(result.task_id)

        @param task_id
        @returns 'ok' or 'locked'
        """
        path = self._lockfile()
        if os.path.exists(path):
            return 'locked'
        with open(self._lockfile(), 'w') as f:
            f.write(task_id)
        return 'ok'
     
    def unlock( self, task_id ):
        """Removes lockfile or complains if can't
        
        This method should be called by celery Task.after_return()
        See "Abstract classes" section of http://celery.readthedocs.org/en/latest/userguide/tasks.html#custom-task-classes
        
        @param task_id
        @returns 'ok', 'not locked', 'task_id miss', 'blocked'
        """
        path = self._lockfile()
        if not os.path.exists(path):
            return 'not locked'
        with open(path, 'r') as f:
            lockfile_task_id = f.read().strip()
        if lockfile_task_id and (lockfile_task_id != task_id):
            return 'task_id miss'
        os.remove(path)
        if os.path.exists(path):
            return 'blocked'
        return 'ok'
    
    def locked( self ):
        """Indicates whether entity is locked; if locked returns celery task_id.
        """
        path = self._lockfile()
        if os.path.exists(path):
            with open(path, 'r') as f:
                task_id = f.read().strip()
            return task_id
        return False
    
    def files_master( self ):
        files = [f for f in self.files if f.role and (f.role == 'master')]
        return sorted(files, key=lambda f: f.sort)
    
    def files_mezzanine( self ):
        files = [f for f in self.files if f.role and (f.role == 'mezzanine')]
        return sorted(files, key=lambda f: f.sort)
    
    def file( self, sha1, newfile=None ):
        """Given a SHA1 hash, get the corresponding file dict.
        
        @param sha1
        @param newfile (optional) If present, updates existing file or appends new one.
        @returns 'added', 'updated', DDRFile, or None
        """
        # update existing file or append
        if sha1 and newfile:
            for f in self.files:
                if sha1 in f.sha1:
                    f = newfile
                    return 'updated'
            self.files.append(newfile)
            return 'added'
        # get a file
        for f in self.files:
            if sha1 in f.sha1:
                return f
        # just do nothing
        return None
    
    def files_log( self, ok=None, msg=None ):
        """Returns log of add_files activity; adds an entry if status,msg given.
        
        @param ok: Boolean. ok or not ok.
        @param msg: Text message.
        @returns log: A text file.
        """
        logpath = os.path.join(self.path, 'addfile.log')
        if ok and msg:
            if ok: ok = 'ok'
            else:  ok = 'not ok'
            entry = '[{}] {} - {}\n'.format(datetime.now().isoformat('T'), ok, msg)
            with open(logpath, 'a') as f:
                f.write(entry)
        log = ''
        with open(logpath, 'r') as f:
            log = f.read()
        return log
    
    @staticmethod
    def create(path):
        """Creates a new entity with the specified entity ID.
        @param path: Absolute path to entity; must end in valid DDR entity id.
        """
        entity = Entity(path)
        for f in ENTITY_FIELDS:
            if hasattr(f, 'name') and hasattr(f, 'initial'):
                setattr(entity, f['name'], f['initial'])
        return entity
    
    def labels_values(self):
        """Generic display
        """
        lv = []
        for f in ENTITY_FIELDS:
            if hasattr(self, f['name']) and f.get('form',None):
                item = {'label': f['form']['label'],
                        'value': getattr(self, f['name'])}
                lv.append(item)
        return lv
    
    def form_data(self):
        """Prep data dict to pass into EntityForm object.
        
        Certain fields may require special processing, which will be performed
        by the function specified in field['prep_func'].
        
        @returns data: dict object as used by Django Form object.
        """
        data = {}
        for f in ENTITY_FIELDS:
            if hasattr(self, f['name']) and f.get('form',None):
                key = f['name']
                value = getattr(self, f['name'])
                # hand off special processing to function specified in ENTITY_FIELDS
                if f.get('prep_func',None):
                    func = f['prep_func']
                    value = func(value)
                # end special processing
                data[key] = value
        if not data.get('created', None):
            data['created'] = datetime.now()
        if not data.get('lastmod', None):
            data['lastmod'] = datetime.now()
        return data
    
    def form_process(self, form):
        """Process cleaned_data coming from EntityForm
        
        Certain fields may require special processing, which will be performed
        by the function specified in field['proc_func'].
        
        @param form
        """
        for f in ENTITY_FIELDS:
            if hasattr(self, f['name']) and f.get('form',None):
                key = f['name']
                cleaned_data = form.cleaned_data[key]
                # hand off special processing to function specified in ENTITY_FIELDS
                if f.get('proc_func',None):
                    func = f['proc_func']
                    cleaned_data = func(cleaned_data)
                # end special processing
                setattr(self, key, cleaned_data)
        # update lastmod
        self.lastmod = datetime.now()

    @staticmethod
    def from_json(entity_abs):
        entity = None
        if os.path.exists(entity_abs):
            entity = DDRLocalEntity(entity_abs)
            entity_uid = entity.id
            entity.load_json(entity.json_path)
            if not entity.id:
                entity.id = entity_uid  # might get overwritten if entity.json is blank
        return entity
    
    def load_json(self, path):
        """Populate Entity data from .json file.
        @param path: Absolute path to entity
        """
        json_data = self.json().data
        
        for ff in ENTITY_FIELDS:
            for f in json_data:
                if f.keys()[0] == ff['name']:
                    setattr(self, f.keys()[0], f.values()[0])
        
        def parsedt(txt):
            d = datetime.now()
            try:
                d = datetime.strptime(txt, settings.DATETIME_FORMAT)
            except:
                try:
                    d = datetime.strptime(txt, settings.TIME_FORMAT)
                except:
                    pass
            return d
            
        # special cases
        if self.created: self.created = parsedt(self.created)
        if self.lastmod: self.lastmod = parsedt(self.lastmod)
        if self.digitize_date: self.digitize_date = parsedt(self.digitize_date)
        # end special cases
        
        # Ensure that every field in ENTITY_FIELDS is represented
        # even if not present in json_data.
        for ff in ENTITY_FIELDS:
            if not hasattr(self, ff['name']):
                setattr(self, ff['name'], ff.get('default',None))
        
        # files, filemeta
        filemetas = {}
        for x in json_data:
            if x.keys()[0] == 'filemeta':
                filemetas = x.values()[0]
        _files = []
        for y in json_data:
            if y.keys()[0] == 'files':
                _files = y.values()[0]
        self.files = []
        for z in _files:
            if z.get('sha1', None):
                m = filemetas.get(z['sha1'], DDRFile.filemeta_blank())
            # This is a little weird since the entity is kinda still being loaded
            # but we only need it for the repo/org/cid/eid and path_rel.
            f = DDRFile.from_entity(self, z, m)
            self.files.append(f)
    
    def dump_json(self):
        """Dump Entity data to .json file.
        @param path: Absolute path to .json file.
        """
        # TODO DUMP FILE AND FILEMETA PROPERLY!!!
        entity = [{'application': 'https://github.com/densho/ddr-local.git',
                   'commit': git_commit(),
                   'release': VERSION,}]
        exceptions = ['files', 'filemeta']
        for f in ENTITY_FIELDS:
            item = {}
            key = f['name']
            val = ''
            dt = datetime(1970,1,1)
            d = date(1970,1,1)
            if hasattr(self, f['name']):
                val = getattr(self, f['name'])
                # special cases
                if val:
                    if (type(val) == type(dt)) or (type(val) == type(d)):
                        val = val.strftime(settings.DATETIME_FORMAT)
                # end special cases
            item[key] = val
            if (key not in exceptions):
                entity.append(item)
        files = []
        for f in self.files:
            fd = {}
            for key in FILE_KEYS:
                if hasattr(f, key):
                    fd[key] = getattr(f, key, None)
            files.append(fd)
        entity.append( {'files':files} )
        filemeta = {}
        for f in self.files:
            fm = {}
            for key in FILEMETA_KEYS:
                if hasattr(f, key) and (key != 'sha1'):
                    fm[key] = getattr(f, key, None)
            filemeta[f.sha1] = fm
        entity.append( {'filemeta':filemeta} )
        # write
        json_pretty = json.dumps(entity, indent=4, separators=(',', ': '), sort_keys=True)
        with open(self.json_path, 'w') as f:
            f.write(json_pretty)
    
    def dump_mets(self):
        """Dump Entity data to mets.xml file.
        """
        NAMESPACES = {
            'mets':  'http://www.loc.gov/METS/',
            'mix':   'http://www.loc.gov/mix/v10',
            'mods':  'http://www.loc.gov/mods/v3',
            'rts':   'http://cosimo.stanford.edu/sdr/metsrights/',
            'xlink': 'http://www.w3.org/1999/xlink',
            'xsi':   'http://www.w3.org/2001/XMLSchema-instance',
        }
        NAMESPACES_TAGPREFIX = {}
        for k,v in NAMESPACES.iteritems():
            NAMESPACES_TAGPREFIX[k] = '{%s}' % v
        NAMESPACES_XPATH = {'mets': NAMESPACES['mets'],}
        NSMAP = {None : NAMESPACES['mets'],}
        NS = NAMESPACES_TAGPREFIX
        ns = NAMESPACES_XPATH
        tree = etree.parse(StringIO(self.mets().xml))
        for f in ENTITY_FIELDS:
            key = f['name']
            value = ''
            if hasattr(self, f['name']):
                value = getattr(self, f['name'])
                # hand off special processing to function specified in ENTITY_FIELDS
                if f.get('mets_func',None):
                    func = f['mets_func']
                    tree = func(tree, NAMESPACES, f, value)
                # end special processing
        xml_pretty = etree.tostring(tree, pretty_print=True)
        with open(self.mets_path, 'w') as f:
            f.write(xml_pretty)



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
                  'access_rel':None,
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
    # path relative to entity
    # (ex: files/ddr-testing-71-6-dd9ec4305d.jpg)
    path = None
    # path relative to /
    # (ex: /var/www/media/base/ddr-testing-71/files/ddr-testing-71-6/files/ddr-testing-71-6-dd9ec4305d.jpg)
    # not saved; constructed on instantiation
    path_abs = None
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
    # access file path relative to entity
    access_rel = FILEMETA_BLANK['access_rel']
    # access file path relative to /
    # not saved; constructed on instantiation
    access_abs = None
    access_size = None
    # entity
    src = None
    repo = None
    org = None
    cid = None
    eid = None
    
    def __init__(self, *args, **kwargs):
        # entity
        if kwargs.get('entity',None):
            self.repo = kwargs['entity'].repo
            self.org = kwargs['entity'].org
            self.cid = kwargs['entity'].cid
            self.eid = kwargs['entity'].eid
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
        self.set_access(FILEMETA_BLANK['access_rel'])
    
    def __repr__(self):
        return "<DDRFile %s (%s)>" % (self.basename, self.basename_orig)
    
    @staticmethod
    def from_entity(entity, phile, meta):
        f = DDRFile()
        # entity
        f.repo = entity.repo
        f.org = entity.org
        f.cid = entity.cid
        f.eid = entity.eid
        # files
        f.set_path(phile.get('path',None), entity)
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
        f.set_access(meta.get('access_rel'), entity)
        if f.path:
            f.basename = os.path.basename(f.path)
            f.src = os.path.join('base', entity.path_rel, f.path)
        return f
    
    def set_path( self, path, entity=None ):
        """
        Reminder:
        self.path is relative to entity
        self.path_abs is relative to filesystem root
        """
        self.path = path
        if entity:
            self.path = self.path.replace(entity.path, '')
        if self.path and (self.path[0] == '/'):
            # remove initial slash (ex: '/files/...')
            self.path = self.path[1:]
        if entity:
            self.path_abs = os.path.join(entity.path, self.path)
            self.src = os.path.join('base', entity.path_rel, self.path)
        if self.path_abs and os.path.exists(self.path_abs):
            self.size = os.path.getsize(self.path_abs)
        self.basename = os.path.basename(self.path)
    
    def set_access( self, access_rel, entity=None ):
        """
        @param access_rel: path relative to entity (ex: 'files/thisfile.ext')
        @param entity: A DDRLocalEntity object (optional)
        """
        if access_rel:
            self.access_rel = access_rel
            if entity:
                self.access_rel = self.access_rel.replace(entity.path, '')
            if self.access_rel and (self.access_rel[0] == '/'):
                # remove initial slash (ex: '/files/...')
                self.access_rel = self.access_rel[1:]
            if entity:
                a = os.path.join(entity.path, self.access_rel)
                if os.path.exists(a):
                    self.access_abs = a
            if self.access_abs and os.path.exists(self.access_abs):
                self.access_size = os.path.getsize(self.access_abs)
    
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
    
    @staticmethod
    def make_access_file( src_abs, append, geometry, options='' ):
        """Attempt to make access file.
        
        Note: uses Imagemagick 'convert'.
        
        @param src_abs: Absolute path to the source file.
        @param append: string to be appended to end of basename.
        @param geometry: String (ex: '200x200')
        @returns status,result: Status bit (0 if OK), Absolute page to access file or error message.
        """
        if not os.path.exists(src_abs):
            return 1,'err: source file does not exist: %s' % src_abs
        result = 'unknown'
        status = -1
        EXTENSION = 'jpg'
        dest_abs = '%s%s.%s' % (os.path.splitext(src_abs)[0], append, EXTENSION)
        if 'pdf' in os.path.splitext(src_abs)[1]:
            pdf_page = '[0]' # only capture the first page
        else:
            pdf_page = ''
        cmd = "convert %s%s -resize '%s' %s" % (src_abs, pdf_page, geometry, dest_abs)
        r = envoy.run(cmd)
        status = r.status_code # 0 means everything's okay
        if status:
            result = r.std_err
        else:
            if os.path.exists(dest_abs):
                if os.path.getsize(dest_abs):
                    result = dest_abs
                elif not os.path.getsize(dest_abs):
                    status = 2
                    result = 'dest file created but zero length'
                    os.remove(dest_abs)
            else:
                result = 'access file was not created: %s' % dest_abs
        return status,result
    
    @staticmethod
    def make_thumbnail( path_abs, geometry, options={} ):
        """Attempt to make thumbnail.
        
        See sorl.thumbnail.templatetags.thumbnail.ThumbnailNode.render 
        https://github.com/sorl/sorl-thumbnail/blob/master/sorl/thumbnail/templatetags/thumbnail.py
        
        from django.core.files import File
        from sorl.thumbnail import default
        from ddrlocal.models import DDRLocalEntity
        entity = DDRLocalEntity.from_json('/var/www/media/base/ddr-testing-61/files/ddr-testing-61-3')
        ef = entity.files[0]
        with open(ef.path, 'r') as f:
            file_ = File(f)
         
        geometry = '200x200'
        thumbnail = default.backend.get_thumbnail(file_, geometry)
        """
        thumbnail = None
        if os.path.exists(path_abs):
            with open(path_abs, 'r') as f:
                file_ = File(f)
            thumbnail = default.backend.get_thumbnail(file_, geometry, options)
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
