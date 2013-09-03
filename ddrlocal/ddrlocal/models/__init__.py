from datetime import datetime, date
import hashlib
import json
import logging
logger = logging.getLogger(__name__)
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
from ddrlocal.models import collection as collectionmodule
from ddrlocal.models import entity as entitymodule
from ddrlocal.models import files as filemodule



COLLECTION_FILES_PREFIX = 'files'
ENTITY_FILES_PREFIX = 'files'

def module_function(module, function_name, value):
    """
    If function is present in ddrlocal.models.entity and is callable,
    pass field info to it and return the result
    """
    if (function_name in dir(module)):
        function = getattr(module, function_name)
        value = function(value)
    return value

def module_xml_function(module, function_name, tree, NAMESPACES, f, value):
    """
    If function is present in ddrlocal.models.entity and is callable,
    pass field info to it and return the result
    """
    if (function_name in dir(module)):
        function = getattr(module, function_name)
        tree = function(tree, NAMESPACES, f, value)
    return tree

def write_json(data, path):
    json_pretty = json.dumps(data, indent=4, separators=(',', ': '), sort_keys=True)
    with open(path, 'w') as f:
        f.write(json_pretty)



MODEL_FIELDS = [
    {
        'name':       '',       # The field name.
        'model_type': str,      # Python data type for the field.
        'default':    '',       # Default value.
        
        'form_type':  '',       # Name of Django forms.Field object.
        'form': {               # Kwargs to be passed to the forms.Field object.
                                # See Django forms documentation.
            'label':     '',    # Pretty, human-readable name of the field.
                                # Note: label is also used in the UI outside of forms.
            'help_text': '',    # Help for hapless users.
            'widget':    '',    # Name of Django forms.Widget object.
            'initial':   '',    # Initial value of field in a form.
        },
        
        'xpath':      "",       # XPath to where field value resides in EAD/METS.
        'xpath_dup':  [],       # Secondary XPath(s). We really should just have one xpath list.
    },
]



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
    
    def cgit_url( self ):
        """Returns cgit URL for collection.
        """
        return '{}/cgit.cgi/{}/'.format(settings.CGIT_URL, self.uid)

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
        for f in collectionmodule.COLLECTION_FIELDS:
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
        
        Certain fields require special processing.
        If a "display_{field}" function is present in the ddrlocal.models.collection
        module it will be executed.
        """
        lv = []
        for f in collectionmodule.COLLECTION_FIELDS:
            if hasattr(self, f['name']) and f.get('form',None):
                key = f['name']
                label = f['form']['label']
                # run display_* functions on field data if present
                value = module_function(collectionmodule,
                                        'display_%s' % key,
                                        getattr(self, f['name']))
                lv.append( {'label':label, 'value':value,} )
        return lv
    
    def form_prep(self):
        """Prep data dict to pass into CollectionForm object.
        
        Certain fields require special processing.
        If a "formprep_{field}" function is present in the ddrlocal.models.collection
        module it will be executed.
        
        @returns data: dict object as used by Django Form object.
        """
        data = {}
        for f in collectionmodule.COLLECTION_FIELDS:
            if hasattr(self, f['name']) and f.get('form',None):
                key = f['name']
                # run formprep_* functions on field data if present
                value = module_function(collectionmodule,
                                        'formprep_%s' % key,
                                        getattr(self, f['name']))
                data[key] = value
        return data
    
    def form_post(self, form):
        """Process cleaned_data coming from CollectionForm
        
        Certain fields require special processing.
        If a "formpost_{field}" function is present in the ddrlocal.models.entity
        module it will be executed.
        
        @param form
        """
        for f in collectionmodule.COLLECTION_FIELDS:
            if hasattr(self, f['name']) and f.get('form',None):
                key = f['name']
                # run formpost_* functions on field data if present
                cleaned_data = module_function(collectionmodule,
                                               'formpost_%s' % key,
                                               form.cleaned_data[key])
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
        for ff in collectionmodule.COLLECTION_FIELDS:
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
        # Ensure that every field in collectionmodule.COLLECTION_FIELDS is represented
        # even if not present in json_data.
        for ff in collectionmodule.COLLECTION_FIELDS:
            if not hasattr(self, ff['name']):
                setattr(self, ff['name'], ff.get('default',None))
    
    def dump_json(self):
        """Dump Collection data to .json file.
        @param path: Absolute path to .json file.
        """
        collection = [{'application': 'https://github.com/densho/ddr-local.git',
                       'commit': git_commit(),
                       'release': VERSION,}]
        for ff in collectionmodule.COLLECTION_FIELDS:
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
        write_json(collection, self.json_path)
    
    def dump_ead(self):
        """Dump Collection data to ead.xml file.
        """
        NAMESPACES = None
        tree = etree.fromstring(self.ead().xml)
        for f in collectionmodule.COLLECTION_FIELDS:
            key = f['name']
            value = ''
            if hasattr(self, f['name']):
                value = getattr(self, key)
                # run ead_* functions on field data if present
                tree = module_xml_function(collectionmodule,
                                           'ead_%s' % key,
                                           tree, NAMESPACES, f,
                                           value)
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
    
    def __repr__(self):
        return "<DDRLocalEntity %s>" % (self.id)
    
    def url( self ):
        return reverse('webui-entity', args=[self.repo, self.org, self.cid, self.eid])

    @staticmethod
    def entity_path(request, repo, org, cid, eid):
        collection_uid = '{}-{}-{}'.format(repo, org, cid)
        entity_uid     = '{}-{}-{}-{}'.format(repo, org, cid, eid)
        collection_abs = os.path.join(settings.MEDIA_BASE, collection_uid)
        entity_abs     = os.path.join(collection_abs, COLLECTION_FILES_PREFIX, entity_uid)
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
        files = [f for f in self.files if hasattr(f,'role') and (f.role == 'master')]
        return sorted(files, key=lambda f: f.sort)
    
    def files_mezzanine( self ):
        files = [f for f in self.files if hasattr(f,'role') and (f.role == 'mezzanine')]
        return sorted(files, key=lambda f: f.sort)
    
    def file( self, repo, org, cid, eid, role, sha1, newfile=None ):
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
            if (f.sha1[:10] == sha1[:10]) and (f.role == role):
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
        if os.path.exists(logpath):
            with open(logpath, 'r') as f:
                log = f.read()
        return log
    
    @staticmethod
    def create(path):
        """Creates a new entity with the specified entity ID.
        @param path: Absolute path to entity; must end in valid DDR entity id.
        """
        entity = Entity(path)
        for f in entitymodule.ENTITY_FIELDS:
            if hasattr(f, 'name') and hasattr(f, 'initial'):
                setattr(entity, f['name'], f['initial'])
        return entity
    
    def labels_values(self):
        """Generic display
        
        Certain fields require special processing.
        If a "display_{field}" function is present in the ddrlocal.models.entity
        module it will be executed.
        """
        lv = []
        for f in entitymodule.ENTITY_FIELDS:
            if hasattr(self, f['name']) and f.get('form',None):
                key = f['name']
                label = f['form']['label']
                # run display_* functions on field data if present
                value = module_function(entitymodule,
                                        'display_%s' % key,
                                        getattr(self, f['name']))
                lv.append( {'label':label, 'value':value,} )
        return lv
    
    def form_prep(self):
        """Prep data dict to pass into EntityForm object.
        
        Certain fields require special processing.
        If a "formprep_{field}" function is present in the ddrlocal.models.entity
        module it will be executed.
        
        @returns data: dict object as used by Django Form object.
        """
        data = {}
        for f in entitymodule.ENTITY_FIELDS:
            if hasattr(self, f['name']) and f.get('form',None):
                key = f['name']
                # run formprep_* functions on field data if present
                value = module_function(entitymodule,
                                        'formprep_%s' % key,
                                        getattr(self, f['name']))
                data[key] = value
        if not data.get('created', None):
            data['created'] = datetime.now()
        if not data.get('lastmod', None):
            data['lastmod'] = datetime.now()
        return data
    
    def form_post(self, form):
        """Process cleaned_data coming from EntityForm
        
        Certain fields require special processing.
        If a "formpost_{field}" function is present in the ddrlocal.models.entity
        module it will be executed.
        
        @param form
        """
        for f in entitymodule.ENTITY_FIELDS:
            if hasattr(self, f['name']) and f.get('form',None):
                key = f['name']
                # run formpost_* functions on field data if present
                cleaned_data = module_function(entitymodule,
                                               'formpost_%s' % key,
                                               form.cleaned_data[key])
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
        
        for ff in entitymodule.ENTITY_FIELDS:
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
        
        # Ensure that every field in entitymodule.ENTITY_FIELDS is represented
        # even if not present in json_data.
        for ff in entitymodule.ENTITY_FIELDS:
            if not hasattr(self, ff['name']):
                setattr(self, ff['name'], ff.get('default',None))
        
        _files = []
        for f in self.files:
            path_abs = os.path.join(self.files_path, f['path_rel'])
            if os.path.exists(path_abs):
                _files.append(DDRFile(path_abs))
        self.files = _files
    
    def dump_json(self):
        """Dump Entity data to .json file.
        @param path: Absolute path to .json file.
        """
        # TODO DUMP FILE AND FILEMETA PROPERLY!!!
        entity = [{'application': 'https://github.com/densho/ddr-local.git',
                   'commit': git_commit(),
                   'release': VERSION,}]
        exceptions = ['files', 'filemeta']
        for f in entitymodule.ENTITY_FIELDS:
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
            for key in ENTITY_FILE_KEYS:
                if hasattr(f, key):
                    fd[key] = getattr(f, key, None)
            files.append(fd)
        entity.append( {'files':files} )
        write_json(entity, self.json_path)
    
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
        for f in entitymodule.ENTITY_FIELDS:
            key = f['name']
            value = ''
            if hasattr(self, f['name']):
                value = getattr(self, f['name'])
                # run mets_* functions on field data if present
                tree = module_xml_function(entitymodule,
                                           'mets_%s' % key,
                                           tree, NAMESPACES, f,
                                           value)
        xml_pretty = etree.tostring(tree, pretty_print=True)
        with open(self.mets_path, 'w') as f:
            f.write(xml_pretty)



ENTITY_FILE_KEYS = ['path_rel',
                    'sha1',
                    'sha256',
                    'md5',
                    'public',]

FILE_KEYS = ['path_rel',
             'basename', 
             'size', 
             'role', 
             'sha1', 
             'sha256', 
             'md5',
             'basename_orig',
             'public',
             'sort',
             'label',
             'thumb',
             'access_rel',
             'xmp',]



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
    # path relative to /
    # (ex: /var/www/media/base/ddr-testing-71/files/ddr-testing-71-6/files/ddr-testing-71-6-dd9ec4305d.jpg)
    # not saved; constructed on instantiation
    path_abs = None
    # files
    # path relative to entity files directory
    # (ex: ddr-testing-71-6-dd9ec4305d.jpg)
    # (ex: subdir/ddr-testing-71-6-dd9ec4305d.jpg)
    path_rel = None
    json_path = None
    basename = None
    basename_orig = ''
    size = None
    role = None
    sha1 = None
    sha256 = None
    md5 = None
    public = 0
    sort = 1
    label = ''
    thumb = -1
    # access file path relative to entity
    access_rel = None
    # access file path relative to /
    # not saved; constructed on instantiation
    access_abs = None
    access_size = None
    xmp = ''
    # entity
    src = None
    repo = None
    org = None
    cid = None
    eid = None
    collection_path = None
    entity_path = None
    entity_files_path = None
    
    def __init__(self, *args, **kwargs):
        """
        """
        # accept either path_abs or path_rel
        if kwargs and kwargs.get('path_abs',None):
            self.path_abs = path_abs
        elif kwargs and kwargs.get('path_rel',None):
            self.path_rel = path_rel
        else:
            if args and args[0]:
                s = os.path.splitext(args[0])
                if os.path.exists(args[0]):
                    self.path_abs = args[0]
                elif (len(s) == 2) and s[0] and s[1]:
                    self.path_rel = args[0]
        if self.path_abs:
            self.basename = os.path.basename(self.path_abs)
        elif self.path_rel:
            self.basename = os.path.basename(self.path_rel)
        # much info is encoded in filename
        if self.basename:
            parts = os.path.splitext(self.basename)[0].split('-')
            self.repo = parts[0]
            self.org = parts[1]
            self.cid = parts[2]
            self.eid = parts[3]
            self.role = parts[4]
            self.sha1 = parts[5]
            self.collection_path = DDRLocalCollection.collection_path(None, self.repo, self.org, self.cid)
            self.entity_path = DDRLocalEntity.entity_path(None, self.repo, self.org, self.cid, self.eid)
            self.entity_files_path = os.path.join(self.entity_path, ENTITY_FILES_PREFIX)
        # get one path if the other not present
        if self.entity_path and self.path_rel and not self.path_abs:
            self.path_abs = os.path.join(self.entity_files_path, self.path_rel)
        elif self.entity_path and self.path_abs and not self.path_rel:
            self.path_rel = self.path_abs.replace(self.entity_files_path, '')
        # clean up path_rel if necessary
        if self.path_rel and (self.path_rel[0] == '/'):
            self.path_rel = self.path_rel[1:]
        # load JSON
        if self.path_abs:
            # file JSON
            self.json_path = os.path.join(os.path.splitext(self.path_abs)[0], '.json')
            self.json_path = self.json_path.replace('/.json', '.json')
            self.load_json()
            access_abs = None
            if self.access_rel and self.entity_path:
                access_abs = os.path.join(self.entity_files_path, self.access_rel)
                if os.path.exists(access_abs):
                    self.access_abs = os.path.join(self.entity_files_path, self.access_rel)
    
    def __repr__(self):
        return "<DDRFile %s (%s)>" % (self.basename, self.basename_orig)
    
    def url( self ):
        return reverse('webui-file', args=[self.repo, self.org, self.cid, self.eid, self.role, self.sha1[:10]])
    
    def media_url( self ):
        if self.path_rel:
            stub = os.path.join(self.entity_files_path.replace(settings.MEDIA_ROOT,''), self.path_rel)
            return '%s%s' % (settings.MEDIA_URL, stub)
        return None
    
    def access_url( self ):
        if self.access_rel:
            stub = os.path.join(self.entity_files_path.replace(settings.MEDIA_ROOT,''), self.access_rel)
            return '%s%s' % (settings.MEDIA_URL, stub)
        return None
    
    @staticmethod
    def file_path(request, repo, org, cid, eid, role, sha1):
        return os.path.join(settings.MEDIA_BASE, '{}-{}-{}-{}-{}-{}'.format(repo, org, cid, eid, role, sha1))
    
    # _lockfile
    # lock
    # unlock
    # locked
    
    # create(path)
    
    # entities/files/???
    
    def labels_values(self):
        """Generic display
        
        Certain fields require special processing.
        If a "display_{field}" function is present in the ddrlocal.models.files
        module it will be executed.
        """
        lv = []
        for f in filemodule.FILE_FIELDS:
            if hasattr(self, f['name']) and f.get('form',None):
                key = f['name']
                label = f['form']['label']
                # run display_* functions on field data if present
                value = module_function(filemodule,
                                        'display_%s' % key,
                                        getattr(self, f['name']))
                lv.append( {'label':label, 'value':value,} )
        return lv
    
    def form_prep(self):
        """Prep data dict to pass into FileForm object.
        
        Certain fields require special processing.
        If a "formprep_{field}" function is present in the ddrlocal.models.files
        module it will be executed.
        
        @returns data: dict object as used by Django Form object.
        """
        data = {}
        for f in filemodule.FILE_FIELDS:
            if hasattr(self, f['name']) and f.get('form',None):
                key = f['name']
                # run formprep_* functions on field data if present
                value = module_function(filemodule,
                                        'formprep_%s' % key,
                                        getattr(self, f['name']))
                data[key] = value
        return data
    
    def form_post(self, form):
        """Process cleaned_data coming from FileForm
        
        Certain fields require special processing.
        If a "formpost_{field}" function is present in the ddrlocal.models.files
        module it will be executed.
        
        @param form
        """
        for f in filemodule.FILE_FIELDS:
            if hasattr(self, f['name']) and f.get('form',None):
                key = f['name']
                # run formpost_* functions on field data if present
                cleaned_data = module_function(filemodule,
                                               'formpost_%s' % key,
                                               form.cleaned_data[key])
                setattr(self, key, cleaned_data)
    
    def load_json(self):
        """Populate File data from .json file.
        @param path: Absolute path to file
        """
        if os.path.exists(self.json_path):
            with open(self.json_path, 'r') as f:
                raw = f.read()
            data = json.loads(raw)
            # everything else
            for ff in filemodule.FILE_FIELDS:
                for f in data:
                    if f.keys()[0] == ff['name']:
                        setattr(self, f.keys()[0], f.values()[0])
    
    def dump_json(self):
        """Dump File data to .json file.
        @param path: Absolute path to .json file.
        """
        # TODO DUMP FILE AND FILEMETA PROPERLY!!!
        file_ = [{'application': 'https://github.com/densho/ddr-local.git',
                  'commit': git_commit(),
                  'release': VERSION,},
                 {'path_rel': self.path_rel},]
        for ff in filemodule.FILE_FIELDS:
            item = {}
            key = ff['name']
            val = ''
            if hasattr(self, ff['name']):
                val = getattr(self, ff['name'])
            item[key] = val
            file_.append(item)
        write_json(file_, self.json_path)
    
    @staticmethod
    def file_name( entity, path_abs, role ):
        """Generate a new name for the specified file; Use only when ingesting a file!
        
        rename files to standard names on ingest:
        %{repo}-%{org}-%{cid}-%{eid}-%{role}%{sha1}.%{ext}
        example: ddr-testing-56-101-master-fb73f9de29.jpg
        
        @param entity
        @param path_abs: Absolute path to the file.
        @param role
        """
        if os.path.exists and os.access(path_abs, os.R_OK):
            ext = os.path.splitext(path_abs)[1]
            sha1 = hash(path_abs, 'sha1')
            if sha1:
                base = '-'.join([
                    entity.repo, entity.org, entity.cid, entity.eid,
                    role,
                    sha1[:10]
                ])
                name = '{}{}'.format(base, ext)
                return name
        return None
    
    def set_path( self, path_rel, entity=None ):
        """
        Reminder:
        self.path_rel is relative to entity
        self.path_abs is relative to filesystem root
        """
        self.path_rel = path_rel
        if entity:
            self.path_rel = self.path_rel.replace(entity.files_path, '')
        if self.path_rel and (self.path_rel[0] == '/'):
            # remove initial slash (ex: '/files/...')
            self.path_rel = self.path_rel[1:]
        if entity:
            self.path_abs = os.path.join(entity.files_path, self.path_rel)
            self.src = os.path.join('base', entity.files_path, self.path_rel)
        if self.path_abs and os.path.exists(self.path_abs):
            self.size = os.path.getsize(self.path_abs)
        self.basename = os.path.basename(self.path_rel)
    
    def set_access( self, access_rel, entity=None ):
        """
        @param access_rel: path relative to entity (ex: 'files/thisfile.ext')
        @param entity: A DDRLocalEntity object (optional)
        """
        if access_rel:
            self.access_rel = access_rel
            if entity:
                self.access_rel = self.access_rel.replace(entity.files_path, '')
            if self.access_rel and (self.access_rel[0] == '/'):
                # remove initial slash (ex: '/files/...')
                self.access_rel = self.access_rel[1:]
            if entity:
                a = os.path.join(entity.files_path, self.access_rel)
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
        
    def dict( self ):
        return self.__dict__
    
    @staticmethod
    def extract_xmp( path_abs ):
        """Attempts to extract XMP data from a file, returns as dict.
        
        @param path_abs: Absolute path to file.
        @return dict NOTE: this is not an XML file!
        """
        xmpfile = libxmp.files.XMPFiles()
        try:
            xmpfile.open_file(path_abs, open_read=True)
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
    def access_file_name( src_abs, append, extension ):
        return '%s%s.%s' % (os.path.splitext(src_abs)[0], append, extension)

    @staticmethod
    def make_access_file( src_abs, append, geometry, options='' ):
        """Attempt to make access file.
        
        Note: uses Imagemagick 'convert' and 'identify'.
        
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
        # test for multiple frames/layers/pages
        # if there are multiple frames, we only want the first one
        frame = ''
        ri = envoy.run('identify %s' % src_abs)
        if ri.status_code:
            return ri.status_code, ri.std_err
        else:
            frames = ri.std_out.strip().split('\n')
            if len(frames) > 1:
                frame = '[0]'
        # resize the file
        cmd = "convert %s%s -resize '%s' %s" % (src_abs, frame, geometry, dest_abs)
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
    
    def links_incoming( self ):
        """List of path_rels of files that link to this file.
        """
        incoming = []
        r = envoy.run('find {} -name "*.json" -print'.format(self.entity_files_path))
        jsons = r.std_out.strip().split('\n')
        for fn in jsons:
            with open(fn, 'r') as f:
                raw = f.read()
            data = json.loads(raw)
            path_rel = None
            for field in data:
                if field.get('path_rel',None):
                    path_rel = field['path_rel']
            for field in data:
                linksraw = field.get('links', None)
                if linksraw:
                    for link in linksraw.strip().split(';'):
                        link = link.strip()
                        if self.basename in link:
                            incoming.append(path_rel)
        return incoming
    
    def links_outgoing( self ):
        """List of path_rels of files this file links to.
        """
        return [link.strip() for link in self.links.strip().split(';')]
    
    def links_all( self ):
        """List of path_rels of files that link to this file or are linked to from this file.
        """
        all = self.links_outgoing()
        for l in self.links_incoming():
            if l not in all:
                all.append(l)
        return all
