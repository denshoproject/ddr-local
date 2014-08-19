from datetime import datetime, date
import hashlib
import json
import logging
logger = logging.getLogger(__name__)
import os
import re
from StringIO import StringIO
import shutil
import sys
import traceback

import envoy
from lxml import etree

from django.conf import settings

from DDR import commands
from DDR import dvcs
from DDR import imaging
from DDR import natural_order_string, natural_sort
from DDR.models import Collection as DDRCollection, Entity as DDREntity
from DDR.models import dissect_path, file_hash, _inheritable_fields, _inherit
from DDR.models import module_function, module_xml_function, write_json
from ddrlocal import VERSION, COMMIT
from ddrlocal.models import collection as collectionmodule
from ddrlocal.models import entity as entitymodule
from ddrlocal.models import files as filemodule
from ddrlocal.models.meta import CollectionJSON, EntityJSON, read_json
from ddrlocal.models.xml import EAD, METS

COLLECTION_FILES_PREFIX = 'files'
ENTITY_FILES_PREFIX = 'files'

MODEL_FIELDS = [
    {
        'name':       '',       # The field name.
        'model_type': str,      # Python data type for the field.
        'default':    '',       # Default value.
        'inheritable': '',      # Whether or not the field is inheritable.
        
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
    Subclass of DDR.models.Collection (renamed).
    Adds functions for reading/writing collection.json and ead.xml,
    preparing/processing Django forms, and displaying data in Django.
    """
    id = 'whatever'
    repo = None
    org = None
    cid = None
    _status = ''
    _astatus = ''
    _unsynced = 0
    ead_path = None
    json_path = None
    ead_path_rel = None
    json_path_rel = None

    def __init__(self, *args, **kwargs):
        """
        >>> c = DDRLocalCollection('/tmp/ddr-testing-123')
        >>> c.uid
        'ddr-testing-123'
        >>> c.repo
        'ddr'
        >>> c.org
        'testing'
        >>> c.cid
        '123'
        >>> c.ead_path_rel
        'ead.xml'
        >>> c.ead_path
        '/tmp/ddr-testing-123/ead.xml'
        >>> c.json_path_rel
        'collection.json'
        >>> c.json_path
        '/tmp/ddr-testing-123/collection.json'
        """
        super(DDRLocalCollection, self).__init__(*args, **kwargs)
        self.id = self.uid
        self.repo = self.id.split('-')[0]
        self.org = self.id.split('-')[1]
        self.cid = self.id.split('-')[2]
        self.ead_path           = self._path_absrel('ead.xml'        )
        self.json_path          = self._path_absrel('collection.json')
        self.ead_path_rel       = self._path_absrel('ead.xml',        rel=True)
        self.json_path_rel      = self._path_absrel('collection.json',rel=True)
    
    def __repr__(self):
        """Returns string representation of object.
        
        >>> c = DDRLocalCollection('/tmp/ddr-testing-123')
        >>> c
        <DDRLocalCollection ddr-testing-123>
        """
        return "<DDRLocalCollection %s>" % (self.id)
    
    @staticmethod
    def create(path):
        """Creates a new collection with the specified collection ID.
        
        Also sets initial field values if present.
        
        >>> c = DDRLocalCollection.create('/tmp/ddr-testing-120')
        
        @param path: Absolute path to collection; must end in valid DDR collection id.
        @returns: Collection object
        """
        collection = DDRLocalCollection(path)
        for f in collectionmodule.COLLECTION_FIELDS:
            if hasattr(f, 'name') and hasattr(f, 'initial'):
                setattr(collection, f['name'], f['initial'])
        return collection
    
    def entities( self, quick=None ):
        """Returns list of the Collection's Entity objects.
        
        >>> c = Collection.from_json('/tmp/ddr-testing-123')
        >>> c.entities()
        [<DDRLocalEntity ddr-testing-123-1>, <DDRLocalEntity ddr-testing-123-2>, ...]
        
        @param quick: Boolean List only titles and IDs
        """
        # empty class used for quick view
        class ListEntity( object ):
            def __repr__(self):
                return "<DDRListEntity %s>" % (self.id)
        entity_paths = []
        if os.path.exists(self.files_path):
            # TODO use cached list if available
            for eid in os.listdir(self.files_path):
                path = os.path.join(self.files_path, eid)
                entity_paths.append(path)
        entity_paths = natural_sort(entity_paths)
        entities = []
        for path in entity_paths:
            if quick:
                # fake Entity with just enough info for lists
                entity_json_path = os.path.join(path,'entity.json')
                if os.path.exists(entity_json_path):
                    with open(entity_json_path, 'r') as f:
                        for line in f.readlines():
                            if '"title":' in line:
                                e = ListEntity()
                                e.id = e.uid = eid = os.path.basename(path)
                                e.repo,e.org,e.cid,e.eid = eid.split('-')
                                # make a miniature JSON doc out of just title line
                                e.title = json.loads('{%s}' % line)['title']
                                entities.append(e)
            else:
                entity = DDRLocalEntity.from_json(path)
                for lv in entity.labels_values():
                    if lv['label'] == 'title':
                        entity.title = lv['value']
                entities.append(entity)
        return entities
    
    def inheritable_fields( self ):
        """Returns list of Collection object's field names marked as inheritable.
        
        >>> c = Collection.from_json('/tmp/ddr-testing-123')
        >>> c.inheritable_fields()
        ['status', 'public', 'rights']
        """
        return _inheritable_fields(collectionmodule.COLLECTION_FIELDS )
    
    def labels_values(self):
        """Apply display_{field} functions to prep object data for the UI.
        
        TODO Move to webui.models
        
        Certain fields require special processing.  For example, structured data
        may be rendered in a template to generate an HTML <ul> list.
        If a "display_{field}" function is present in the ddrlocal.models.collection
        module the contents of the field will be passed to it
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
        """Apply formprep_{field} functions to prep data dict to pass into CollectionForm object.
        
        TODO Move to webui.models
        
        Certain fields require special processing.  Data may need to be massaged
        and prepared for insertion into particular Django form objects.
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
        """Apply formpost_{field} functions to process cleaned_data from CollectionForm
        
        TODO Move to webui.models
        
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
        # update record_lastmod
        self.record_lastmod = datetime.now()
    
    def json( self ):
        """Returns a ddrlocal.models.meta.CollectionJSON object
        
        TODO Do we really need this?
        """
        #if not os.path.exists(self.json_path):
        #    CollectionJSON.create(self.json_path)
        return CollectionJSON(self)
    
    @staticmethod
    def from_json(collection_abs):
        """Instantiates a DDRLocalCollection object, loads data from collection.json.
        
        >>> c = DDRLocalCollection.from_json('/tmp/ddr-testing-123')
        """
        collection = DDRLocalCollection(collection_abs)
        collection_uid = collection.id  # save this just in case
        collection.load_json(collection.json_path)
        if not collection.id:
            # id gets overwritten if collection.json is blank
            collection.id = collection_uid
        return collection
    
    def load_json(self, path):
        """Populate Collection data from .json file and COLLECTION_FIELDS.
        
        Loads the JSON datafile then goes through COLLECTION_FIELDS,
        turning data in the JSON file into attributes of the object.
        
        @param path: Absolute path to collection directory
        """
        json_data = self.json().data
        for ff in collectionmodule.COLLECTION_FIELDS:
            for f in json_data:
                if hasattr(f, 'keys') and (f.keys()[0] == ff['name']):
                    setattr(self, f.keys()[0], f.values()[0])
        # special cases
        if hasattr(self, 'record_created') and self.record_created:
            self.record_created = datetime.strptime(self.record_created, settings.DATETIME_FORMAT)
        else:
            self.record_created = datetime.now()
        if hasattr(self, 'record_lastmod') and self.record_lastmod:
            self.record_lastmod = datetime.strptime(self.record_lastmod, settings.DATETIME_FORMAT)
        else:
            self.record_lastmod = datetime.now()
        # end special cases
        # Ensure that every field in collectionmodule.COLLECTION_FIELDS is represented
        # even if not present in json_data.
        for ff in collectionmodule.COLLECTION_FIELDS:
            if not hasattr(self, ff['name']):
                setattr(self, ff['name'], ff.get('default',None))
    
    def dump_json(self, path=None, template=False):
        """Dump Collection data to .json file.
        
        TODO This should not actually write the JSON! It should return JSON to the code that calls it.
        
        @param path: [optional] Alternate file path.
        @param template: [optional] Boolean. If true, write default values for fields.
        """
        collection = [{'application': 'https://github.com/densho/ddr-local.git',
                       'commit': COMMIT,
                       'release': VERSION,
                       'git': dvcs.git_version(self.path),}]
        template_passthru = ['id', 'record_created', 'record_lastmod']
        for ff in collectionmodule.COLLECTION_FIELDS:
            item = {}
            key = ff['name']
            val = ''
            if template and (key not in template_passthru):
                # write default values
                val = ff['form']['initial']
            elif hasattr(self, ff['name']):
                # write object's values
                val = getattr(self, ff['name'])
                # special cases
                if key in ['record_created', 'record_lastmod']:
                    # JSON requires dates to be represented as strings
                    val = val.strftime(settings.DATETIME_FORMAT)
                # end special cases
            item[key] = val
            collection.append(item)
        if not path:
            path = self.json_path
        write_json(collection, path)
    
    def ead( self ):
        """Returns a ddrlocal.models.xml.EAD object for the collection.
        
        TODO Do we really need this?
        """
        if not os.path.exists(self.ead_path):
            EAD.create(self.ead_path)
        return EAD(self)
    
    def dump_ead(self):
        """Dump Collection data to ead.xml file.
        
        TODO render a Django/Jinja template instead of using lxml
        TODO This should not actually write the XML! It should return XML to the code that calls it.
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
    json_path = None
    mets_path = None
    json_path_rel = None
    mets_path_rel = None
    
    def __init__(self, *args, **kwargs):
        super(DDRLocalEntity, self).__init__(*args, **kwargs)
        self.id = self.uid
        self.repo = self.id.split('-')[0]
        self.org = self.id.split('-')[1]
        self.cid = self.id.split('-')[2]
        self.eid = self.id.split('-')[3]
        self.json_path          = self._path_absrel('entity.json')
        self.mets_path          = self._path_absrel('mets.xml'   )
        self.json_path_rel      = self._path_absrel('entity.json',rel=True)
        self.mets_path_rel      = self._path_absrel('mets.xml',   rel=True)
        self._files = []
    
    def __repr__(self):
        return "<DDRLocalEntity %s>" % (self.id)
    
    def files_master( self ):
        files = [f for f in self.files if hasattr(f,'role') and (f.role == 'master')]
        return sorted(files, key=lambda f: f.sort)
    
    def files_mezzanine( self ):
        files = [f for f in self.files if hasattr(f,'role') and (f.role == 'mezzanine')]
        return sorted(files, key=lambda f: f.sort)
    
    def detect_file_duplicates( self, role ):
        """Returns list of file dicts that appear in Entity.files more than once
        
        NOTE: This function looks only at the list of file dicts in entity.json;
        it does not examine the filesystem.
        """
        duplicates = []
        for x,f in enumerate(self.files):
            for y,f2 in enumerate(self.files):
                if (f2 == f) and (f.role == role) and (y != x) and (f not in duplicates):
                    duplicates.append(f)
        return duplicates
    
    def rm_file_duplicates( self ):
        """Remove duplicates from the Entity.files (._files) list of dicts.
        
        Technically, it rebuilds the last without the duplicates.
        NOTE: See note for detect_file_duplicates().
        """
        # regenerate files list
        new_files = []
        for f in self._files:
            if f not in new_files:
                new_files.append(f)
        self.files = new_files
        # reload objects
        self._load_file_objects()
    
    def file( self, repo, org, cid, eid, role, sha1, newfile=None ):
        """Given a SHA1 hash, get the corresponding file dict.
        
        @param sha1
        @param newfile (optional) If present, updates existing file or appends new one.
        @returns 'added', 'updated', DDRLocalFile, or None
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
    
    def _addfile_log_path( self ):
        """Generates path to collection addfiles.log.
        
        Previously each entity had its own addfile.log.
        Going forward each collection will have a single log file.
            /STORE/log/REPO-ORG-CID-addfile.log
        
        @returns: absolute path to logfile
        """
        logpath = os.path.join(
            settings.LOG_DIR, 'addfile', self.parent_uid, '%s.log' % self.id)
        if not os.path.exists(os.path.dirname(logpath)):
            os.makedirs(os.path.dirname(logpath))
        return logpath
    
    def files_log( self, ok=None, msg=None ):
        """Returns log of add_files activity; adds an entry if status,msg given.
        
        @param ok: Boolean. ok or not ok.
        @param msg: Text message.
        @returns log: A text file.
        """
        logpath = self._addfile_log_path()
        if ok:
            ok = 'ok'
        else:
            ok = 'not ok'
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
    
    def inherit( self, parent ):
        _inherit( parent, self )

    def inheritable_fields( self ):
        return _inheritable_fields(entitymodule.ENTITY_FIELDS)
    
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
        if not data.get('record_created', None):
            data['record_created'] = datetime.now()
        if not data.get('record_lastmod', None):
            data['record_lastmod'] = datetime.now()
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
        # update record_lastmod
        self.record_lastmod = datetime.now()
    
    def json( self ):
        if not os.path.exists(self.json_path):
            EntityJSON.create(self.json_path)
        return EntityJSON(self)

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
    
    def _load_file_objects( self ):
        """Replaces list of file info dicts with list of DDRLocalFile objects
        
        IMPORTANT: original 
        """
        # keep copy of the list for detect_file_duplicates()
        self._files = [f for f in self.files]
        self.files = []
        for f in self._files:
            path_abs = os.path.join(self.files_path, f['path_rel'])
            self.files.append(DDRLocalFile(path_abs=path_abs))
    
    def load_json(self, path):
        """Populate Entity data from .json file.
        @param path: Absolute path to entity
        """
        json_data = self.json().data
        
        for ff in entitymodule.ENTITY_FIELDS:
            for f in json_data:
                if hasattr(f, 'keys') and (f.keys()[0] == ff['name']):
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
        if hasattr(self, 'record_created') and self.record_created: self.record_created = parsedt(self.record_created)
        if hasattr(self, 'record_lastmod') and self.record_lastmod: self.record_lastmod = parsedt(self.record_lastmod)
        # end special cases
        
        # Ensure that every field in entitymodule.ENTITY_FIELDS is represented
        # even if not present in json_data.
        for ff in entitymodule.ENTITY_FIELDS:
            if not hasattr(self, ff['name']):
                setattr(self, ff['name'], ff.get('default',None))
        
        # replace list of file paths with list of DDRLocalFile objects
        self._load_file_objects()
    
    def dump_json(self, path=None, template=False):
        """Dump Entity data to .json file.
        
        TODO This should not actually write the JSON! It should return JSON to the code that calls it.
        
        @param path: [optional] Alternate file path.
        @param template: [optional] Boolean. If true, write default values for fields.
        """
        entity = [{'application': 'https://github.com/densho/ddr-local.git',
                   'commit': COMMIT,
                   'release': VERSION,
                   'git': dvcs.git_version(self.parent_path),}]
        exceptions = ['files', 'filemeta']
        template_passthru = ['id', 'record_created', 'record_lastmod']
        for ff in entitymodule.ENTITY_FIELDS:
            item = {}
            key = ff['name']
            val = ''
            dt = datetime(1970,1,1)
            d = date(1970,1,1)
            if template and (key not in template_passthru) and hasattr(ff,'form'):
                # write default values
                val = ff['form']['initial']
            elif hasattr(self, ff['name']):
                # write object's values
                val = getattr(self, ff['name'])
                # special cases
                if val:
                    if (type(val) == type(dt)) or (type(val) == type(d)):
                        val = val.strftime(settings.DATETIME_FORMAT)
                # end special cases
            item[key] = val
            if (key not in exceptions):
                entity.append(item)
        files = []
        if not template:
            for f in self.files:
                fd = {}
                for key in ENTITY_FILE_KEYS:
                    if hasattr(f, key):
                        fd[key] = getattr(f, key, None)
                files.append(fd)
        entity.append( {'files':files} )
        if not path:
            path = self.json_path
        write_json(entity, path)
    
    def mets( self ):
        if not os.path.exists(self.mets_path):
            METS.create(self.mets_path)
        return METS(self)
    
    def dump_mets(self):
        """Dump Entity data to mets.xml file.
        
        TODO render a Django/Jinja template instead of using lxml
        TODO This should not actually write the XML! It should return XML to the code that calls it.
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
    
    def add_file( self, git_name, git_mail, src_path, role, data, agent='' ):
        """Add file to entity
        
        This method breaks out of OOP and manipulates entity.json directly.
        Thus it needs to lock to prevent other edits while it does its thing.
        Writes a log to ${entity}/addfile.log, formatted in pseudo-TAP.
        This log is returned along with a DDRLocalFile object.
        
        @param src_path: Absolute path to an uploadable file.
        @param role: Keyword of a file role.
        @param git_name: Username of git committer.
        @param git_mail: Email of git committer.
        @param agent: (optional) Name of software making the change.
        @return file_ DDRLocalFile object
        """
        def crash(msg):
            """Write to addfile log and raise an exception."""
            self.files_log(0, msg)
            raise Exception(msg)
        
        self.files_log(1, 'ddrlocal.models.DDRLocalEntity.add_file: START')
        self.files_log(1, 'entity: %s' % self.id)
        self.files_log(1, 'data: %s' % data)
        
        self.files_log(1, 'Checking files/dirs')
        # source file
        self.files_log(1, 'src_path: %s' % src_path)
        if not os.path.exists(src_path): crash('src_path does not exist')
        if not os.access(src_path, os.R_OK): crash('src_path not readable')
        src_basename = os.path.basename(src_path)
        self.files_log(1, 'src_basename: %s' % src_basename)
        # temporary working dir
        tmp_dir = os.path.join(
            settings.MEDIA_BASE, 'tmp', 'file-add',
            self.parent_uid, self.id)
        self.files_log(1, 'tmp_dir: %s' % tmp_dir)
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)
        if not os.path.exists(tmp_dir): crash('tmp_dir does not exist')
        if not os.access(tmp_dir, os.W_OK): crash('tmp_dir not writable')
        # destination dir in repo-entity
        dest_dir = self.files_path
        self.files_log(1, 'dest_dir: %s' % dest_dir)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        if not os.path.exists(dest_dir): crash('dest_dir does not exist')
        if not os.access(dest_dir, os.W_OK): crash('dest_dir not writable')
        
        self.files_log(1, 'Extracting XMP data')
        xmp = imaging.extract_xmp(src_path)
        if xmp:
            self.files_log(1, 'we got some XMP')
        else:
            self.files_log(1, 'no XMP here')
        
        self.files_log(1, 'Copying to work dir')
        size = os.path.getsize(src_path)
        self.files_log(1, 'size: %s' % size)
        tmp_path = os.path.join(tmp_dir, src_basename)
        self.files_log(1, 'cp %s %s' % (src_path, tmp_path))
        shutil.copy(src_path, tmp_path)
        os.chmod(tmp_path, 0644)
        if not os.path.exists(tmp_path):
            crash('Copy to work dir failed %s %s' % (src_path, tmp_path))
        
        self.files_log(1, 'Checksumming')
        sha1   = file_hash(tmp_path, 'sha1');   self.files_log(1, 'sha1: %s' % sha1)
        md5    = file_hash(tmp_path, 'md5');    self.files_log(1, 'md5: %s' % md5)
        sha256 = file_hash(tmp_path, 'sha256'); self.files_log(1, 'sha256: %s' % sha256)
        if not sha1 and md5 and sha256:
            crash('Could not calculate checksums')
        
        # rename file now that we have checksum
        dest_basename = DDRLocalFile.file_name(
            self, src_path, role, sha1)  # NOTE: runs checksum if no sha1 arg!
        tmp_path_renamed = os.path.join(os.path.dirname(tmp_path), dest_basename)
        self.files_log(1, 'Renaming %s -> %s' % (os.path.basename(tmp_path), dest_basename))
        os.rename(tmp_path, tmp_path_renamed)
        if not os.path.exists(tmp_path_renamed) and not os.path.exists(tmp_path):
            crash('File rename failed: %s -> %s' % (tmp_path, tmp_path_renamed))
        
        self.files_log(1, 'Making access file')
        access_filename = DDRLocalFile.access_filename(src_path)
        # Access file fails should not stop the process but we want
        # to capture tracebacks in the log
        try:
            tmp_access_path = imaging.thumbnail(
                src_path,
                os.path.join(tmp_dir, os.path.basename(access_filename)),
                geometry=settings.ACCESS_FILE_GEOMETRY)
        except:
            tmp_access_path = None
            self.files_log(0, traceback.format_exc().strip())
        
        # file object
        dest_path = os.path.join(dest_dir, dest_basename)
        f = DDRLocalFile(path_abs=dest_path)
        f.basename_orig = src_basename
        self.files_log(1, 'Created DDRLocalFile: %s' % f)
        self.files_log(1, 'f.path_abs: %s' % f.path_abs)
        f.xmp = xmp
        f.size = size
        f.sha1 = sha1
        f.md5 = md5
        f.sha256 = sha256
        f.role = role
        if tmp_access_path and os.path.exists(tmp_access_path):
            self.files_log(1, 'Attaching access file')
            #dest_access_path = os.path.join('files', os.path.basename(tmp_access_path))
            #self.files_log(1, 'dest_access_path: %s' % dest_access_path)
            f.set_access(tmp_access_path, self)
            self.files_log(1, 'f.access_rel: %s' % f.access_rel)
            self.files_log(1, 'f.access_abs: %s' % f.access_abs)
        else:
            self.files_log(0, 'no access file')
        # form data
        for field in data:
            setattr(f, field, data[field])
        # attach file to entity
        self.files_log(1, 'Attaching file to entity')
        self.files.append(f)
        
        self.files_log(1, 'Writing file and entity metadata')
        tmp_file_json = os.path.join(tmp_dir, os.path.basename(f.json_path))
        tmp_entity_json = os.path.join(tmp_dir, os.path.basename(self.json_path))
        self.files_log(1, tmp_file_json)
        f.dump_json(path=tmp_file_json)
        if not os.path.exists(tmp_file_json):
            crash('Could not write file metadata %s' % tmp_file_json)
        self.files_log(1, tmp_entity_json)
        self.dump_json(path=tmp_entity_json)
        if not os.path.exists(tmp_entity_json):
            crash('Could not write entity metadata %s' % tmp_entity_json)
        # grab copy of original entity metadata in case something goes wrong
        self.files_log(1, 'Backing up entity metadata')
        entity_json_backup = os.path.join(tmp_dir, 'entity.json.orig')
        shutil.copy(self.json_path, entity_json_backup)
        if not os.path.exists(entity_json_backup):
            crash('Could not backup entity metadata %s' % entity_json_backup)
        
        self.files_log(1, 'Moving files to dest_dir')
        new_files = []
        if tmp_access_path and os.path.exists(tmp_access_path):
            new_files.append([tmp_access_path, f.access_abs])
        new_files.append([tmp_path_renamed, f.path_abs])
        new_files.append([tmp_file_json, f.json_path])
        failures = []
        for tmp,dest in new_files:
            self.files_log(1, 'mv %s %s' % (tmp,dest))
            os.rename(tmp,dest)
            if not os.path.exists(dest):
                self.files_log(0, 'FAIL')
                failures.append(tmp)
                break
        # one of new_files failed to copy, so move all back to tmp
        if failures:
            self.files_log(0, '%s failures: %s' % (len(failures), failures))
            self.files_log(0, 'moving files back to tmp_dir')
            try:
                for tmp,dest in new_files:
                    self.files_log(1, 'mv %s %s' % (dest,tmp))
                    os.rename(dest,tmp)
                    if not os.path.exists(tmp) and not os.path.exists(dest):
                        self.files_log(0, 'FAIL')
            except:
                msg = "Unexpected error:", sys.exc_info()[0]
                self.files_log(0, msg)
                raise
            finally:
                crash('Failed to place one or more files to destination repo')
        # entity metadata will only be copied if everything else was moved
        self.files_log(1, 'mv %s %s' % (tmp_entity_json, self.json_path))
        os.rename(tmp_entity_json, self.json_path)
        if not os.path.exists(self.json_path):
            crash('Failed to place entity.json in destination repo')
        
        # commit
        git_files = [
            self.json_path_rel,
            f.json_path_rel
        ]
        annex_files = [
            f.basename
        ]
        if f.access_rel:
            annex_files.append(f.access_rel)
        self.files_log(1, 'entity_annex_add(%s, %s, %s, %s, %s, %s, %s, %s)' % (
            git_name, git_mail,
            self.parent_path, self.id,
            git_files, annex_files,
            agent, self))
        try:
            exit,status = commands.entity_annex_add(
                git_name, git_mail,
                self.parent_path, self.id, git_files, annex_files,
                agent=agent, entity=self)
            self.files_log(1, 'status: %s' % status)
            self.files_log(1, 'ddrlocal.models.DDRLocalEntity.add_file: FINISHED')
        except:
            # COMMIT FAILED! try to pick up the pieces
            # print traceback to addfile log
            with open(self._addfile_log_path(), 'a') as f:
                traceback.print_exc(file=f)
            # mv files back to tmp_dir
            self.files_log(0, 'status: %s' % status)
            self.files_log(0, 'Cleaning up...')
            for tmp,dest in new_files:
                self.files_log(0, 'mv %s %s' % (dest,tmp))
                os.rename(dest,tmp)
            # restore backup of original entity metadata
            self.files_log(0, 'cp %s %s' % (entity_json_backup, self.json_path))
            shutil.copy(entity_json_backup, self.json_path)
            self.files_log(0, 'finished cleanup. good luck...')
            raise
        return f.__dict__
    
    def add_access( self, git_name, git_mail, ddrfile, agent='' ):
        """Generate new access file for entity
        
        This method breaks out of OOP and manipulates entity.json directly.
        Thus it needs to lock to prevent other edits while it does its thing.
        Writes a log to ${entity}/addfile.log, formatted in pseudo-TAP.
        This log is returned along with a DDRLocalFile object.
        
        @param ddrfile: DDRLocalFile
        @param git_name: Username of git committer.
        @param git_mail: Email of git committer.
        @param agent: (optional) Name of software making the change.
        @return file_ DDRLocalFile object
        """
        def crash(msg):
            """Write to addfile log and raise an exception."""
            self.files_log(0, msg)
            raise Exception(msg)
        
        src_path = ddrfile.path_abs
        self.files_log(1, 'ddrlocal.models.DDRLocalEntity.add_access: START')
        self.files_log(1, 'entity: %s' % self.id)
        self.files_log(1, 'src_path: %s' % src_path)

        self.files_log(1, 'Checking files/dirs')
        # source file
        self.files_log(1, 'src_path: %s' % src_path)
        if not os.path.exists(src_path): crash('src_path does not exist')
        if not os.access(src_path, os.R_OK): crash('src_path not readable')
        src_basename = os.path.basename(src_path)
        self.files_log(1, 'src_basename: %s' % src_basename)
        # temporary working dir
        tmp_dir = os.path.join(
            settings.MEDIA_BASE, 'tmp', 'file-add',
            self.parent_uid, self.id)
        self.files_log(1, 'tmp_dir: %s' % tmp_dir)
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)
        if not os.path.exists(tmp_dir): crash('tmp_dir does not exist')
        if not os.access(tmp_dir, os.W_OK): crash('tmp_dir not writable')
        # destination dir in repo-entity
        dest_dir = self.files_path
        self.files_log(1, 'dest_dir: %s' % dest_dir)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        if not os.path.exists(dest_dir): crash('dest_dir does not exist')
        if not os.access(dest_dir, os.W_OK): crash('dest_dir not writable')
        
        self.files_log(1, 'Making access file')
        access_filename = DDRLocalFile.access_filename(src_path)
        tmp_access_path = imaging.thumbnail(
            src_path,
            os.path.join(tmp_dir, os.path.basename(access_filename)),
            geometry=settings.ACCESS_FILE_GEOMETRY)
        self.files_log(1, 'tmp_access_path: %s' % tmp_access_path)
        # unlike add_file, it's a fail if there's no access file
        if (not tmp_access_path) or (not os.path.exists(tmp_access_path)):
            crash('Failed to make an access file from %s' % src_path)
        
        # file object
        f = ddrfile
        self.files_log(1, 'Attaching access file')
        f.set_access(tmp_access_path, self)
        self.files_log(1, 'f.access_rel: %s' % f.access_rel)
        self.files_log(1, 'f.access_abs: %s' % f.access_abs)
        
        self.files_log(1, 'Writing file metadata')
        tmp_file_json = os.path.join(tmp_dir, os.path.basename(f.json_path))
        self.files_log(1, tmp_file_json)
        f.dump_json(path=tmp_file_json)
        if not os.path.exists(tmp_file_json):
            crash('Could not write file metadata %s' % tmp_file_json)
        # grab copy of file metadata in case something goes wrong
        self.files_log(1, 'Backing up file metadata')
        file_json_backup = '%s.orig' % tmp_file_json
        shutil.copy(f.json_path, file_json_backup)
        if not os.path.exists(file_json_backup):
            crash('Could not back up file metadata %s' % file_json_backup)
        
        self.files_log(1, 'Moving files to dest_dir')
        new_files = []
        new_files.append([tmp_access_path, f.access_abs])
        failures = []
        for tmp,dest in new_files:
            self.files_log(1, 'mv %s %s' % (tmp,dest))
            os.rename(tmp,dest)
            if not os.path.exists(dest):
                self.files_log(0, 'FAIL')
                failures.append(tmp)
                break
        # one of new_files failed to copy, so move all back to tmp
        if failures:
            self.files_log(0, '%s failures: %s' % (len(failures), failures))
            self.files_log(0, 'moving files back to tmp_dir')
            try:
                for tmp,dest in new_files:
                    self.files_log(1, 'mv %s %s' % (dest,tmp))
                    os.rename(dest,tmp)
                    if not os.path.exists(tmp) and not os.path.exists(dest):
                        self.files_log(0, 'FAIL')
            except:
                msg = "Unexpected error:", sys.exc_info()[0]
                self.files_log(0, msg)
                raise
            finally:
                crash('Failed to place one or more files to destination repo')
        # file metadata will only be copied if everything else was moved
        self.files_log(1, 'mv %s %s' % (tmp_file_json, f.json_path))
        os.rename(tmp_file_json, f.json_path)
        if not os.path.exists(f.json_path):
            crash('Failed to place file metadata in destination repo')
        
        # commit
        git_files = [
            f.json_path_rel
        ]
        annex_files = [
            f.access_rel
        ]
        self.files_log(1, 'entity_annex_add(%s, %s, %s, %s, %s, %s, %s, %s)' % (
            git_name, git_mail,
            self.parent_path, self.id,
            git_files, annex_files,
            agent, self))
        try:
            exit,status = commands.entity_annex_add(
                git_name, git_mail,
                self.parent_path, self.id, git_files, annex_files,
                agent=agent, entity=self)
            self.files_log(1, 'status: %s' % status)
            self.files_log(1, 'ddrlocal.models.DDRLocalEntity.add_file: FINISHED')
        except:
            # COMMIT FAILED! try to pick up the pieces
            # print traceback to addfile log
            with open(self._addfile_log_path(), 'a') as f:
                traceback.print_exc(file=f)
            # mv files back to tmp_dir
            self.files_log(0, 'status: %s' % status)
            self.files_log(0, 'Cleaning up...')
            for tmp,dest in new_files:
                self.files_log(0, 'mv %s %s' % (dest,tmp))
                os.rename(dest,tmp)
            # restore backup of original file metadata
            self.files_log(0, 'cp %s %s' % (file_json_backup, f.json_path))
            shutil.copy(file_json_backup, f.json_path)
            self.files_log(0, 'finished cleanup. good luck...')
            raise
        return f.__dict__
    
    def checksums( self, algo ):
        """Calculates hash checksums for the Entity's files.
        
        Gets hashes from FILE.json metadata if the file(s) are absent
        from the filesystem (i.e. git-annex file symlinks).
        Overrides DDR.models.Entity.checksums.
        """
        checksums = []
        if algo not in self.checksum_algorithms():
            raise Error('BAD ALGORITHM CHOICE: {}'.format(algo))
        for f in self.file_paths():
            cs = None
            fpath = os.path.join(self.files_path, f)
            # git-annex files are present
            if os.path.exists(fpath) and not os.path.islink(fpath):
                cs = file_hash(fpath, algo)
            # git-annex files NOT present - get checksum from entity._files
            # WARNING: THIS MODULE SHOULD NOT KNOW ANYTHING ABOUT HIGHER-LEVEL CODE!
            elif os.path.islink(fpath) and hasattr(self, '_files'):
                for fdict in self._files:
                    if os.path.basename(fdict['path_rel']) == os.path.basename(fpath):
                        cs = fdict[algo]
            if cs:
                checksums.append( (cs, fpath) )
        return checksums



ENTITY_FILE_KEYS = ['path_rel',
                    'role',
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

class DDRLocalFile( object ):
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
    json_path_rel = None
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
    links = None
    
    def __init__(self, *args, **kwargs):
        """
        IMPORTANT: If at all possible, use the "path_abs" kwarg!!
        You *can* just pass in an absolute path. It will *appear* to work.
        This horrible function will attempt to infer the path but will
        probably get it wrong and fail silently!
        TODO refactor and simplify this horrible code!
        """
        # accept either path_abs or path_rel
        if kwargs and kwargs.get('path_abs',None):
            self.path_abs = kwargs['path_abs']
        elif kwargs and kwargs.get('path_rel',None):
            self.path_rel = kwargs['path_rel']
        else:
            if args and args[0]:
                s = os.path.splitext(args[0])
                if os.path.exists(args[0]):  # <<< Causes problems with missing git-annex files
                    self.path_abs = args[0]  #     Use path_abs arg!!!
                elif (len(s) == 2) and s[0] and s[1]:
                    self.path_rel = args[0]
        if self.path_abs:
            self.basename = os.path.basename(self.path_abs)
        elif self.path_rel:
            self.basename = os.path.basename(self.path_rel)
        # IMPORTANT: path_rel is the link between Entity and File
        # It MUST be present in entity.json and file.json or lots of
        # things will break!
        # NOTE: path_rel is basically the same as basename
        if self.path_abs and not self.path_rel:
            self.path_rel = self.basename
        # much info is encoded in filename
        if self.basename:
            parts = os.path.splitext(self.basename)[0].split('-')
            self.repo = parts[0]
            self.org = parts[1]
            self.cid = parts[2]
            self.eid = parts[3]
            # NOTE: we get role from filename and also from JSON data, if available
            self.role = parts[4]
            self.sha1 = parts[5]
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
            p = dissect_path(self.path_abs)
            self.collection_path = p.collection_path
            self.entity_path = p.entity_path
            self.entity_files_path = os.path.join(self.entity_path, ENTITY_FILES_PREFIX)
            # file JSON
            self.json_path = os.path.join(os.path.splitext(self.path_abs)[0], '.json')
            self.json_path = self.json_path.replace('/.json', '.json')
            self.json_path_rel = self.json_path.replace(self.collection_path, '')
            if self.json_path_rel[0] == '/':
                self.json_path_rel = self.json_path_rel[1:]
            self.load_json()
            access_abs = None
            if self.access_rel and self.entity_path:
                access_abs = os.path.join(self.entity_files_path, self.access_rel)
                if os.path.exists(access_abs):
                    self.access_abs = os.path.join(self.entity_files_path, self.access_rel)
    
    def __repr__(self):
        return "<DDRLocalFile %s (%s)>" % (self.basename, self.basename_orig)
    
    # _lockfile
    # lock
    # unlock
    # locked
    
    # create(path)
    
    # entities/files/???
    
    def files_rel( self, collection_path ):
        """Returns list of the file, its metadata JSON, and access file, relative to collection.
        
        @param collection_path
        @returns: list of relative file paths
        """
        if collection_path[-1] != '/':
            collection_path = '%s/' % collection_path
        paths = [ ]
        if self.path_abs and os.path.exists(self.path_abs) and (collection_path in self.path_abs):
            paths.append(self.path_abs.replace(collection_path, ''))
        if self.json_path and os.path.exists(self.json_path) and (collection_path in self.json_path):
            paths.append(self.json_path.replace(collection_path, ''))
        if self.access_abs and os.path.exists(self.access_abs) and (collection_path in self.access_abs):
            paths.append(self.access_abs.replace(collection_path, ''))
        return paths
    
    def present( self ):
        """Indicates whether or not the original file is currently present in the filesystem.
        """
        if self.path_abs and os.path.exists(self.path_abs):
            return True
        return False
    
    def access_present( self ):
        """Indicates whether or not the access file is currently present in the filesystem.
        """
        if self.access_abs and os.path.exists(self.access_abs):
            return True
        return False
    
    def inherit( self, parent ):
        _inherit( parent, self )
    
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
    
    @staticmethod
    def from_json(file_json):
        """
        @param file_json: Absolute path to the JSON metadata file
        """
        # This is complicated: The file object has to be created with
        # the path to the file to which the JSON metadata file refers.
        file_abs = None
        fid = os.path.splitext(os.path.basename(file_json))[0]
        fstub = '%s.' % fid
        for filename in os.listdir(os.path.dirname(file_json)):
            if (fstub in filename) and not ('json' in filename):
                file_abs = os.path.join(os.path.dirname(file_json), filename)
        # Now load the object
        file_ = None
        if os.path.exists(file_abs) or os.path.islink(file_abs):
            file_ = DDRLocalFile(file_abs)
            file_.load_json()
        return file_
    
    def load_json(self):
        """Populate File data from .json file.
        @param path: Absolute path to file
        """
        if os.path.exists(self.json_path):
            data = read_json(self.json_path)
            # everything else
            for ff in filemodule.FILE_FIELDS:
                for f in data:
                    if hasattr(f, 'keys') and (f.keys()[0] == ff['name']):
                        setattr(self, f.keys()[0], f.values()[0])
    
    def dump_json(self, path=None):
        """Dump File data to .json file.
        
        TODO This should not actually write the JSON! It should return JSON to the code that calls it.
        
        @param path: Absolute path to .json file.
        """
        if not path:
            path = self.json_path
        # TODO DUMP FILE AND FILEMETA PROPERLY!!!
        file_ = [{'application': 'https://github.com/densho/ddr-local.git',
                  'commit': COMMIT,
                  'release': VERSION,
                  'git': dvcs.git_version(self.collection_path),},
                 {'path_rel': self.path_rel},]
        for ff in filemodule.FILE_FIELDS:
            item = {}
            key = ff['name']
            val = ''
            if hasattr(self, ff['name']):
                val = getattr(self, ff['name'])
            item[key] = val
            file_.append(item)
        write_json(file_, path)
    
    @staticmethod
    def file_name( entity, path_abs, role, sha1=None ):
        """Generate a new name for the specified file; Use only when ingesting a file!
        
        rename files to standard names on ingest:
        %{repo}-%{org}-%{cid}-%{eid}-%{role}%{sha1}.%{ext}
        example: ddr-testing-56-101-master-fb73f9de29.jpg
        
        SHA1 is optional so it can be passed in by a calling process that has already
        generated it.
        
        @param entity
        @param path_abs: Absolute path to the file.
        @param role
        @param sha1: SHA1 hash (optional)
        """
        if os.path.exists and os.access(path_abs, os.R_OK):
            ext = os.path.splitext(path_abs)[1]
            if not sha1:
                sha1 = file_hash(path_abs, 'sha1')
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
        @param access_rel: path relative to entity files dir (ex: 'thisfile.ext')
        @param entity: A DDRLocalEntity object (optional)
        """
        self.access_rel = os.path.basename(access_rel)
        if entity:
            self.access_abs = os.path.join(entity.files_path, self.access_rel)
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
    def access_filename( src_abs ):
        """Generate access filename base on source filename.
        
        @param src_abs: Absolute path to source file.
        @returns: Absolute path to access file
        """
        return '%s%s.%s' % (
            os.path.splitext(src_abs)[0],
            settings.ACCESS_FILE_APPEND,
            'jpg')
    
    def links_incoming( self ):
        """List of path_rels of files that link to this file.
        """
        incoming = []
        cmd = 'find {} -name "*.json" -print'.format(self.entity_files_path)
        r = envoy.run(cmd)
        jsons = []
        if r.std_out:
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
        if self.links:
            return [link.strip() for link in self.links.strip().split(';')]
        return []
    
    def links_all( self ):
        """List of path_rels of files that link to this file or are linked to from this file.
        """
        links = self.links_outgoing()
        for l in self.links_incoming():
            if l not in links:
                links.append(l)
        return links
