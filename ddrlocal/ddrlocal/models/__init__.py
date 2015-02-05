import ConfigParser
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

from DDR import changelog
from DDR import commands
from DDR import dvcs
from DDR import imaging
from DDR import format_json, natural_order_string, natural_sort
from DDR.models import Collection as DDRCollection, Entity as DDREntity
from DDR.models import dissect_path, file_hash, _inheritable_fields, _inherit
from DDR.models import module_function, module_path, module_xml_function

from ddrlocal import VERSION, COMMIT
from ddrlocal.models import collection as collectionmodule
from ddrlocal.models import entity as entitymodule
from ddrlocal.models import files as filemodule
from ddrlocal.models.meta import CollectionJSON, EntityJSON, read_json
from ddrlocal.models.xml import EAD, METS

from DDR import CONFIG_FILES, NoConfigError
config = ConfigParser.ConfigParser()
configs_read = config.read(CONFIG_FILES)
if not configs_read:
    raise NoConfigError('No config file!')

REPO_MODELS_PATH = config.get('cmdln','repo_models_path')

if REPO_MODELS_PATH not in sys.path:
    sys.path.append(REPO_MODELS_PATH)
try:
    from repo_models import collection as collectionmodule
    from repo_models import entity as entitymodule
    from repo_models import files as filemodule
except ImportError:
    from ddrlocal.models import collection as collectionmodule
    from ddrlocal.models import entity as entitymodule
    from ddrlocal.models import files as filemodule

MEDIA_BASE = config.get('cmdln','media_base')
LOG_DIR = config.get('local', 'log_dir')
TIME_FORMAT = config.get('cmdln','time_format')
DATETIME_FORMAT = config.get('cmdln','datetime_format')
ACCESS_FILE_GEOMETRY = config.get('cmdln','access_file_geometry')
ACCESS_FILE_APPEND = config.get('cmdln','access_file_append')

COLLECTION_FILES_PREFIX = 'files'
ENTITY_FILES_PREFIX = 'files'



def from_json(model, path):
    """
    @param model: DDRLocalCollection, DDRLocalEntity, or DDRLocalFile
    @param path: absolute path to the object(not the JSON file)
    """
    logging.debug('from_json(%s, %s)' % (model, path))
    document = None
    if os.path.exists(path):
        document = model(path)
        document_uid = document.id  # save this just in case
        with open(document.json_path, 'r') as f:
            document.load_json(f.read())
        if not document.id:
            # id gets overwritten if document.json is blank
            document.id = document_uid
    return document

def load_json(document, module, json_text):
    """Populates object from JSON-formatted text.
    
    Goes through module.FIELDS turning data in the JSON file into
    object attributes.
    
    @param document: Collection/Entity/File object.
    @param module: collection/entity/file module from 'ddr' repo.
    @param json_text: JSON-formatted text
    @returns: dict
    """
    json_data = json.loads(json_text)
    ## software and commit metadata
    #if data:
    #    setattr(document, 'json_metadata', data[0])
    # field values from JSON
    for mf in module.FIELDS:
        for f in json_data:
            if hasattr(f, 'keys') and (f.keys()[0] == mf['name']):
                setattr(document, f.keys()[0], f.values()[0])
    # Fill in missing fields with default values from module.FIELDS.
    # Note: should not replace fields that are just empty.
    for mf in module.FIELDS:
        if not hasattr(document, mf['name']):
            setattr(document, mf['name'], mf.get('default',None))
    return json_data

def prep_json(obj, module, template=False,
              template_passthru=['id', 'record_created', 'record_lastmod'],
              exceptions=[]):
    """Arranges object data in list-of-dicts format before serialization.
    
    DDR keeps data in Git is to take advantage of versioning.  Python
    dicts store data in random order which makes it impossible to
    meaningfully compare diffs of the data over time.  DDR thus stores
    data as an alphabetically arranged list of dicts, with several
    exceptions.
    
    The first dict in the list is not part of the object itself but
    contains metadata about the state of the DDR application at the time
    the file was last written: the Git commit of the app, the release
    number, and the versions of Git and git-annex used.
    
    Python data types that cannot be represented in JSON (e.g. datetime)
    are converted into strings.
    
    @param obj: Collection/Entity/File object.
    @param module: collection/entity/file module from 'ddr' repo.
    @param template: Boolean True if object to be used as blank template.
    @param template_passthru: list
    @param exceptions: list
    @returns: dict
    """
    data = []
    for mf in module.FIELDS:
        item = {}
        key = mf['name']
        val = ''
        if template and (key not in template_passthru) and hasattr(mf,'form'):
            # write default values
            val = mf['form']['initial']
        elif hasattr(obj, mf['name']):
            # write object's values
            val = getattr(obj, mf['name'])
            # special cases
            if val:
                # JSON requires dates to be represented as strings
                if hasattr(val, 'fromtimestamp') and hasattr(val, 'strftime'):
                    val = val.strftime(DATETIME_FORMAT)
            # end special cases
        item[key] = val
        if key not in exceptions:
            data.append(item)
    return data

def labels_values(document, module):
    """Apply display_{field} functions to prep object data for the UI.
    
    TODO Move to webui.models
    
    Certain fields require special processing.  For example, structured data
    may be rendered in a template to generate an HTML <ul> list.
    If a "display_{field}" function is present in the ddrlocal.models.collection
    module the contents of the field will be passed to it
    
    @param document: Collection, Entity, File document object
    @param module: collection, entity, files model definitions module
    @returns: list
    """
    lv = []
    for f in module.FIELDS:
        if hasattr(document, f['name']) and f.get('form',None):
            key = f['name']
            label = f['form']['label']
            # run display_* functions on field data if present
            value = module_function(
                module,
                'display_%s' % key,
                getattr(document, f['name'])
            )
            lv.append( {'label':label, 'value':value,} )
    return lv

def form_prep(document, module):
    """Apply formprep_{field} functions to prep data dict to pass into DDRForm object.
    
    TODO Move to webui.models
    
    Certain fields require special processing.  Data may need to be massaged
    and prepared for insertion into particular Django form objects.
    If a "formprep_{field}" function is present in the ddrlocal.models.collection
    module it will be executed.
    
    @param document: Collection, Entity, File document object
    @param module: collection, entity, files model definitions module
    @returns data: dict object as used by Django Form object.
    """
    data = {}
    for f in module.FIELDS:
        if hasattr(document, f['name']) and f.get('form',None):
            key = f['name']
            # run formprep_* functions on field data if present
            value = module_function(
                module,
                'formprep_%s' % key,
                getattr(document, f['name'])
            )
            data[key] = value
    return data
    
def form_post(document, module, form):
    """Apply formpost_{field} functions to process cleaned_data from CollectionForm
    
    TODO Move to webui.models
    
    Certain fields require special processing.
    If a "formpost_{field}" function is present in the ddrlocal.models.entity
    module it will be executed.
    
    @param document: Collection, Entity, File document object
    @param module: collection, entity, files model definitions module
    @param form: DDRForm object
    """
    for f in module.FIELDS:
        if hasattr(document, f['name']) and f.get('form',None):
            key = f['name']
            # run formpost_* functions on field data if present
            cleaned_data = module_function(
                module,
                'formpost_%s' % key,
                form.cleaned_data[key]
            )
            setattr(document, key, cleaned_data)
    # update record_lastmod
    if hasattr(document, 'record_lastmod'):
        document.record_lastmod = datetime.now()

def document_metadata(module, document_repo_path):
    """Metadata for the ddrlocal/ddrcmdln and models definitions used.
    
    @param module: collection, entity, files model definitions module
    @param document_repo_path: Absolute path to root of document's repo
    @returns: dict
    """
    data = {
        'application': 'https://github.com/densho/ddr-local.git',
        'app_commit': dvcs.latest_commit(os.path.dirname(__file__)),
        'app_release': VERSION,
        'models_commit': dvcs.latest_commit(module_path(module)),
        'git_version': dvcs.git_version(document_repo_path),
    }
    return data

def cmp_model_definition_commits(document, module):
    """Indicate document's model defs are newer or older than module's.
    
    Prepares repository and document/module commits to be compared
    by DDR.dvcs.cmp_commits.  See that function for how to interpret
    the results.
    Note: if a document has no defs commit it is considered older
    than the module.
    
    @param document: A Collection, Entity, or File object.
    @param module: A collection, entity, or files module.
    @returns: int
    """
    def parse(txt):
        return txt.strip().split(' ')[0]
    module_commit_raw = dvcs.latest_commit(module_path(module))
    module_defs_commit = parse(module_commit_raw)
    if not module_defs_commit:
        return 128
    doc_metadata = getattr(document, 'json_metadata', {})
    document_commit_raw = doc_metadata.get('models_commit','')
    document_defs_commit = parse(document_commit_raw)
    if not document_defs_commit:
        return -1
    repo = dvcs.repository(module_path(module))
    return dvcs.cmp_commits(repo, document_defs_commit, module_defs_commit)

def cmp_model_definition_fields(document_json, module):
    """Indicate whether module adds or removes fields from document
    
    @param document_json: Raw contents of document *.json file
    @param module: A collection, entity, or files module.
    @returns: list,list Lists of added,removed field names.
    """
    # First item in list is document metadata, everything else is a field.
    document_fields = [field.keys()[0] for field in json.loads(document_json)[1:]]
    module_fields = [field['name'] for field in getattr(module, 'FIELDS')]
    # models.load_json() uses MODULE.FIELDS, so get list of fields
    # directly from the JSON document.
    added = [field for field in module_fields if field not in document_fields]
    removed = [field for field in document_fields if field not in module_fields]
    return added,removed


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
        for f in collectionmodule.FIELDS:
            if hasattr(f, 'name') and hasattr(f, 'initial'):
                setattr(collection, f['name'], f['initial'])
        return collection
    
    def model_def_commits( self ):
        return cmp_model_definition_commits(self, collectionmodule)
    
    def model_def_fields( self ):
        with open(self.json_path, 'r') as f:
            text = f.read()
        return cmp_model_definition_fields(text, collectionmodule)
    
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
        return _inheritable_fields(collectionmodule.FIELDS )
    
    def labels_values(self):
        """Apply display_{field} functions to prep object data for the UI.
        """
        return labels_values(self, collectionmodule)
    
    def form_prep(self):
        """Apply formprep_{field} functions to prep data dict to pass into DDRForm object.
        
        @returns data: dict object as used by Django Form object.
        """
        data = form_prep(self, collectionmodule)
        return data
    
    def form_post(self, form):
        """Apply formpost_{field} functions to process cleaned_data from DDRForm
        
        @param form: DDRForm object
        """
        form_post(self, collectionmodule, form)
    
    def json( self ):
        """Returns a ddrlocal.models.meta.CollectionJSON object
        
        TODO Do we really need this?
        """
        #if not os.path.exists(self.json_path):
        #    CollectionJSON.create(self.json_path)
        return CollectionJSON(self)
    
    @staticmethod
    def from_json(collection_abs):
        """Creates a DDRLocalCollection and populates with data from JSON file.
        
        @param collection_abs: Absolute path to collection directory.
        @returns: DDRLocalCollection
        """
        return from_json(DDRLocalCollection, collection_abs)
    
    def load_json(self, json_text):
        """Populates Collection from JSON-formatted text.
        
        Goes through COLLECTION_FIELDS, turning data in the JSON file into
        object attributes.
        
        @param json_text: JSON-formatted text
        """
        load_json(self, collectionmodule, json_text)
        # special cases
        if hasattr(self, 'record_created') and self.record_created:
            self.record_created = datetime.strptime(self.record_created, DATETIME_FORMAT)
        else:
            self.record_created = datetime.now()
        if hasattr(self, 'record_lastmod') and self.record_lastmod:
            self.record_lastmod = datetime.strptime(self.record_lastmod, DATETIME_FORMAT)
        else:
            self.record_lastmod = datetime.now()
    
    def dump_json(self, template=False, doc_metadata=False):
        """Dump Collection data to JSON-formatted text.
        
        @param template: [optional] Boolean. If true, write default values for fields.
        @param doc_metadata: boolean. Insert document_metadata().
        @returns: JSON-formatted text
        """
        data = prep_json(self, collectionmodule, template=template)
        if doc_metadata:
            data.insert(0, document_metadata(collectionmodule, self.path))
        return format_json(data)
    
    def write_json(self):
        """Write JSON file to disk.
        """
        json_data = self.dump_json(doc_metadata=True)
        # TODO use codecs.open utf-8
        with open(self.json_path, 'w') as f:
            f.write(json_data)
    
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
        for f in collectionmodule.FIELDS:
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



class EntityAddFileLogger():
    logpath = None
    
    def entry(self, ok, msg ):
        """Returns log of add_files activity; adds an entry if status,msg given.
        
        @param ok: Boolean. ok or not ok.
        @param msg: Text message.
        @returns log: A text file.
        """
        entry = '[{}] {} - {}\n'.format(datetime.now().isoformat('T'), ok, msg)
        with open(self.logpath, 'a') as f:
            f.write(entry)
    
    def ok(self, msg): self.entry('ok', msg)
    def not_ok(self, msg): self.entry('not ok', msg)
    
    def log(self):
        log = ''
        if os.path.exists(self.logpath):
            with open(self.logpath, 'r') as f:
                log = f.read()
        return log

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
    _file_objects = 0
    _file_objects_loaded = 0
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
        self._file_objects = []
    
    def __repr__(self):
        return "<DDRLocalEntity %s>" % (self.id)
    
    def model_def_commits( self ):
        return cmp_model_definition_commits(self, entitymodule)
    
    def model_def_fields( self ):
        with open(self.json_path, 'r') as f:
            text = f.read()
        return cmp_model_definition_fields(text, entitymodule)
    
    @staticmethod
    def create(path):
        """Creates a new entity with the specified entity ID.
        @param path: Absolute path to entity; must end in valid DDR entity id.
        """
        entity = Entity(path)
        for f in entitymodule.FIELDS:
            if hasattr(f, 'name') and hasattr(f, 'initial'):
                setattr(entity, f['name'], f['initial'])
        return entity
    
    def inherit( self, parent ):
        _inherit( parent, self )

    def inheritable_fields( self ):
        return _inheritable_fields(entitymodule.FIELDS)
    
    def labels_values(self):
        """Apply display_{field} functions to prep object data for the UI.
        """
        return labels_values(self, entitymodule)
    
    def form_prep(self):
        """Apply formprep_{field} functions to prep data dict to pass into DDRForm object.
        
        @returns data: dict object as used by Django Form object.
        """
        data = form_prep(self, entitymodule)
        if not data.get('record_created', None):
            data['record_created'] = datetime.now()
        if not data.get('record_lastmod', None):
            data['record_lastmod'] = datetime.now()
        return data
    
    def form_post(self, form):
        """Apply formpost_{field} functions to process cleaned_data from DDRForm
        
        @param form: DDRForm object
        """
        form_post(self, entitymodule, form)
    
    def json( self ):
        if not os.path.exists(self.json_path):
            EntityJSON.create(self.json_path)
        return EntityJSON(self)
    
    @staticmethod
    def from_json(entity_abs):
        """Creates a DDRLocalEntity and populates with data from JSON file.
        
        @param entity_abs: Absolute path to entity dir.
        @returns: DDRLocalEntity
        """
        return from_json(DDRLocalEntity, entity_abs)

    def load_json(self, json_text):
        """Populate Entity data from JSON-formatted text.
        
        @param json_text: JSON-formatted text
        """
        load_json(self, entitymodule, json_text)
        # special cases
        def parsedt(txt):
            d = datetime.now()
            try:
                d = datetime.strptime(txt, DATETIME_FORMAT)
            except:
                try:
                    d = datetime.strptime(txt, TIME_FORMAT)
                except:
                    pass
            return d
        if hasattr(self, 'record_created') and self.record_created: self.record_created = parsedt(self.record_created)
        if hasattr(self, 'record_lastmod') and self.record_lastmod: self.record_lastmod = parsedt(self.record_lastmod)
        self.rm_file_duplicates()

    def dump_json(self, template=False, doc_metadata=False):
        """Dump Entity data to JSON-formatted text.
        
        @param template: [optional] Boolean. If true, write default values for fields.
        @param doc_metadata: boolean. Insert document_metadata().
        @returns: JSON-formatted text
        """
        data = prep_json(self, entitymodule,
                         exceptions=['files', 'filemeta'],
                         template=template,)
        if doc_metadata:
            data.insert(0, document_metadata(entitymodule, self.parent_path))
        files = []
        if not template:
            for f in self.files:
                fd = {}
                for key in ENTITY_FILE_KEYS:
                    val = None
                    if hasattr(f, key):
                        val = getattr(f, key, None)
                    elif f.get(key,None):
                        val = f[key]
                    if val != None:
                        fd[key] = val
                files.append(fd)
        data.append( {'files':files} )
        return format_json(data)

    def write_json(self):
        """Write JSON file to disk.
        """
        json_data = self.dump_json(doc_metadata=True)
        # TODO use codecs.open utf-8
        with open(self.json_path, 'w') as f:
            f.write(json_data)

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
        for f in entitymodule.FIELDS:
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
    
    def load_file_objects( self ):
        """Replaces list of file info dicts with list of DDRLocalFile objects
        
        TODO Don't call in loop - causes all file .JSONs to be loaded!
        """
        self._file_objects = []
        for f in self.files:
            if f and f.get('path_rel',None):
                path_abs = os.path.join(self.files_path, f['path_rel'])
                file_ = DDRLocalFile(path_abs=path_abs)
                with open(file_.json_path, 'r') as j:
                    file_.load_json(j.read())
                self._file_objects.append(file_)
        # keep track of how many times this gets loaded...
        self._file_objects_loaded = self._file_objects_loaded + 1
    
    def files_master( self ):
        self.load_file_objects()
        files = [f for f in self._file_objects if hasattr(f,'role') and (f.role == 'master')]
        return sorted(files, key=lambda f: f.sort)
    
    def files_mezzanine( self ):
        self.load_file_objects()
        files = [f for f in self._file_objects if hasattr(f,'role') and (f.role == 'mezzanine')]
        return sorted(files, key=lambda f: f.sort)
    
    def detect_file_duplicates( self, role ):
        """Returns list of file dicts that appear in Entity.files more than once
        
        NOTE: This function looks only at the list of file dicts in entity.json;
        it does not examine the filesystem.
        """
        duplicates = []
        for x,f in enumerate(self.files):
            for y,f2 in enumerate(self.files):
                if (f != f2) and (f['path_rel'] == f2['path_rel']) and (f2 not in duplicates):
                    duplicates.append(f)
        return duplicates
    
    def rm_file_duplicates( self ):
        """Remove duplicates from the Entity.files (._files) list of dicts.
        
        Technically, it rebuilds the last without the duplicates.
        NOTE: See note for detect_file_duplicates().
        """
        # regenerate files list
        new_files = []
        for f in self.files:
            if f not in new_files:
                new_files.append(f)
        self.files = new_files
        # reload objects
        self.load_file_objects()
    
    def file( self, repo, org, cid, eid, role, sha1, newfile=None ):
        """Given a SHA1 hash, get the corresponding file dict.
        
        @param sha1
        @param newfile (optional) If present, updates existing file or appends new one.
        @returns 'added', 'updated', DDRLocalFile, or None
        """
        self.load_file_objects()
        # update existing file or append
        if sha1 and newfile:
            for f in self.files:
                if sha1 in f.sha1:
                    f = newfile
                    return 'updated'
            self.files.append(newfile)
            return 'added'
        # get a file
        for f in self._file_objects:
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
            LOG_DIR, 'addfile', self.parent_uid, '%s.log' % self.id)
        if not os.path.exists(os.path.dirname(logpath)):
            os.makedirs(os.path.dirname(logpath))
        return logpath
    
    def addfile_logger( self ):
        log = EntityAddFileLogger()
        log.logpath = self._addfile_log_path()
        return log
    
    def add_file( self, src_path, role, data, git_name, git_mail, agent='' ):
        """Add file to entity
        
        This method breaks out of OOP and manipulates entity.json directly.
        Thus it needs to lock to prevent other edits while it does its thing.
        Writes a log to ${entity}/addfile.log, formatted in pseudo-TAP.
        This log is returned along with a DDRLocalFile object.
        
        IMPORTANT: Files are only staged! Be sure to commit!
        
        @param src_path: Absolute path to an uploadable file.
        @param role: Keyword of a file role.
        @param data: 
        @param git_name: Username of git committer.
        @param git_mail: Email of git committer.
        @param agent: (optional) Name of software making the change.
        @return DDRLocalFile,repo,log
        """
        f = None
        repo = None
        log = self.addfile_logger()
        
        def crash(msg):
            """Write to addfile log and raise an exception."""
            log.not_ok(msg)
            raise Exception(msg)
        
        log.ok('ddrlocal.models.DDRLocalEntity.add_file: START')
        log.ok('entity: %s' % self.id)
        log.ok('data: %s' % data)
        
        tmp_dir = os.path.join(
            MEDIA_BASE, 'tmp', 'file-add', self.parent_uid, self.id)
        dest_dir = self.files_path
        
        log.ok('Checking files/dirs')
        def check_dir(label, path, mkdir=False, perm=os.W_OK):
            log.ok('%s: %s' % (label, path))
            if mkdir and not os.path.exists(path):
                os.makedirs(path)
            if not os.path.exists(path): crash('%s does not exist' % label)
            if not os.access(path, perm): crash('%s not has permission %s' % (label, permission))
        check_dir('src_path', src_path, mkdir=False, perm=os.R_OK)
        check_dir('tmp_dir', tmp_dir, mkdir=True, perm=os.W_OK)
        check_dir('dest_dir', dest_dir, mkdir=True, perm=os.W_OK)
        
        log.ok('Checksumming')
        sha1   = file_hash(src_path, 'sha1');   log.ok('sha1: %s' % sha1)
        md5    = file_hash(src_path, 'md5');    log.ok('md5: %s' % md5)
        sha256 = file_hash(src_path, 'sha256'); log.ok('sha256: %s' % sha256)
        if not sha1 and md5 and sha256:
            crash('Could not calculate checksums')
        
        # final basename
        dest_basename = DDRLocalFile.file_name(
            self, src_path, role, sha1)  # NOTE: runs checksum if no sha1 arg!
        dest_path = os.path.join(dest_dir, dest_basename)
        
        # file object
        f = DDRLocalFile(path_abs=dest_path)
        f.basename_orig = os.path.basename(src_path)
        f.size = os.path.getsize(src_path)
        f.role = role
        f.sha1 = sha1
        f.md5 = md5
        f.sha256 = sha256
        log.ok('Created DDRLocalFile: %s' % f)
        log.ok('f.path_abs: %s' % f.path_abs)
        log.ok('f.basename_orig: %s' % f.basename_orig)
        log.ok('f.size: %s' % f.size)
        # form data
        for field in data:
            setattr(f, field, data[field])
        
        log.ok('Copying to work dir')
        tmp_path = os.path.join(tmp_dir, f.basename_orig)
        log.ok('cp %s %s' % (src_path, tmp_path))
        shutil.copy(src_path, tmp_path)
        os.chmod(tmp_path, 0644)
        if not os.path.exists(tmp_path):
            crash('Copy to work dir failed %s %s' % (src_path, tmp_path))
        
        # rename file
        tmp_path_renamed = os.path.join(os.path.dirname(tmp_path), dest_basename)
        log.ok('Renaming %s -> %s' % (os.path.basename(tmp_path), dest_basename))
        os.rename(tmp_path, tmp_path_renamed)
        if not os.path.exists(tmp_path_renamed) and not os.path.exists(tmp_path):
            crash('File rename failed: %s -> %s' % (tmp_path, tmp_path_renamed))
        
        log.ok('Extracting XMP data')
        f.xmp = imaging.extract_xmp(src_path)
        
        log.ok('Making access file')
        access_filename = DDRLocalFile.access_filename(tmp_path_renamed)
        tmp_access_path = None
        try:
            tmp_access_path = imaging.thumbnail(
                src_path,
                os.path.join(tmp_dir, os.path.basename(access_filename)),
                geometry=ACCESS_FILE_GEOMETRY)
        except:
            # write traceback to log and continue on
            log.not_ok(traceback.format_exc().strip())
        if tmp_access_path and os.path.exists(tmp_access_path):
            log.ok('Attaching access file')
            #dest_access_path = os.path.join('files', os.path.basename(tmp_access_path))
            #log.ok('dest_access_path: %s' % dest_access_path)
            f.set_access(tmp_access_path, self)
            log.ok('f.access_rel: %s' % f.access_rel)
            log.ok('f.access_abs: %s' % f.access_abs)
        else:
            log.not_ok('no access file')
        
        log.ok('Attaching file to entity')
        self.files.append(f)
        
        log.ok('Writing file metadata')
        tmp_file_json = os.path.join(tmp_dir, os.path.basename(f.json_path))
        log.ok(tmp_file_json)
        with open(tmp_file_json, 'w') as fj:
            fj.write(f.dump_json())
        if not os.path.exists(tmp_file_json):
            crash('Could not write file metadata %s' % tmp_file_json)
        log.ok('Writing entity metadata')
        tmp_entity_json = os.path.join(tmp_dir, os.path.basename(self.json_path))
        log.ok(tmp_entity_json)
        with open(tmp_entity_json, 'w') as ej:
            ej.write(self.dump_json())
        if not os.path.exists(tmp_entity_json):
            crash('Could not write entity metadata %s' % tmp_entity_json)
        
        # WE ARE NOW MAKING CHANGES TO THE REPO ------------------------
        
        log.ok('Moving files to dest_dir')
        new_files = [
            [tmp_path_renamed, f.path_abs],
            [tmp_file_json, f.json_path],
        ]
        if tmp_access_path and os.path.exists(tmp_access_path):
            new_files.append([tmp_access_path, f.access_abs])
        mvfiles_failures = []
        for tmp,dest in new_files:
            log.ok('mv %s %s' % (tmp,dest))
            os.rename(tmp,dest)
            if not os.path.exists(dest):
                log.not_ok('FAIL')
                mvfiles_failures.append(tmp)
                break
        # one of new_files failed to copy, so move all back to tmp
        if mvfiles_failures:
            log.not_ok('%s failures: %s' % (len(mvfiles_failures), mvfiles_failures))
            log.not_ok('moving files back to tmp_dir')
            try:
                for tmp,dest in new_files:
                    log.ok('mv %s %s' % (dest,tmp))
                    os.rename(dest,tmp)
                    if not os.path.exists(tmp) and not os.path.exists(dest):
                        log.not_ok('FAIL')
            except:
                msg = "Unexpected error:", sys.exc_info()[0]
                log.not_ok(msg)
                raise
            finally:
                crash('Failed to place one or more files to destination repo')
        # entity metadata will only be copied if everything else was moved
        log.ok('mv %s %s' % (tmp_entity_json, self.json_path))
        os.rename(tmp_entity_json, self.json_path)
        if not os.path.exists(self.json_path):
            crash('Failed to place entity.json in destination repo')
        
        # stage files
        git_files = [self.json_path_rel, f.json_path_rel]
        annex_files = [f.path_abs.replace('%s/' % f.collection_path, '')]
        if f.access_abs:
            annex_files.append(f.access_abs.replace('%s/' % f.collection_path, ''))
        to_stage = len(git_files + annex_files)
        stage_ok = False
        try:
            repo = dvcs.repository(f.collection_path)
            log.ok(repo)
            log.ok('Staging %s files to the repo' % to_stage)
            dvcs.stage(repo, git_files, annex_files)
            staged = len(dvcs.list_staged(repo))
            if staged == to_stage:
                log.ok('%s files staged' % staged)
                stage_ok = True
            else:
                log.not_ok('%s files staged (should be %s)' % (staged, to_stage))
        except:
            # FAILED! print traceback to addfile log
            entrails = traceback.format_exc().strip()
            log.not_ok(entrails)
            with open(self._addfile_log_path(), 'a') as f:
                f.write(entrails)
        finally:
            if not stage_ok:
                log.not_ok('File staging aborted. Cleaning up...')
                # try to pick up the pieces
                # mv files back to tmp_dir
                for tmp,dest in new_files:
                    log.not_ok('mv %s %s' % (dest,tmp))
                    os.rename(dest,tmp)
                log.not_ok('finished cleanup. good luck...')
                raise crash('Add file aborted, see log file for details.')
        
        # IMPORTANT: Files are only staged! Be sure to commit!
        # IMPORTANT: changelog is not staged!
        return f,repo,log
    
    def add_file_commit(self, file_, repo, log, git_name, git_mail, agent):
        staged = dvcs.list_staged(repo)
        modified = dvcs.list_modified(repo)
        if staged and not modified:
            log.ok('All files staged.')
            
            log.ok('Updating changelog')
            path = file_.path_abs.replace('{}/'.format(self.path), '')
            changelog_messages = ['Added entity file {}'.format(path)]
            if agent:
                changelog_messages.append('@agent: %s' % agent)
            changelog.write_changelog_entry(
                self.changelog_path, changelog_messages, git_name, git_mail)
            log.ok('git add %s' % self.changelog_path_rel)
            git_files = [self.changelog_path_rel]
            dvcs.stage(repo, git_files)
            
            log.ok('Committing')
            commit = dvcs.commit(repo, 'Added entity file(s)', agent)
            log.ok('commit: {}'.format(commit.hexsha))
            committed = dvcs.list_committed(repo, commit)
            committed.sort()
            log.ok('files committed:     {}'.format(committed))
            
        else:
            log.not_ok('%s files staged, %s files modified' % (len(staged),len(modified)))
            log.not_ok('staged %s' % staged)
            log.not_ok('modified %s' % modified)
            log.not_ok('Can not commit!')
            raise Exception()
        return file_,repo,log
    
    def add_access( self, ddrfile, git_name, git_mail, agent='' ):
        """Generate new access file for entity
        
        This method breaks out of OOP and manipulates entity.json directly.
        Thus it needs to lock to prevent other edits while it does its thing.
        Writes a log to ${entity}/addfile.log, formatted in pseudo-TAP.
        This log is returned along with a DDRLocalFile object.
        
        TODO Refactor this function! It is waaay too long!
        
        @param ddrfile: DDRLocalFile object
        @param git_name: Username of git committer.
        @param git_mail: Email of git committer.
        @param agent: (optional) Name of software making the change.
        @return file_ DDRLocalFile object
        """
        f = ddrfile
        repo = None
        log = self.addfile_logger()
        
        def crash(msg):
            """Write to addfile log and raise an exception."""
            log.not_ok(msg)
            raise Exception(msg)
        
        log.ok('ddrlocal.models.DDRLocalEntity.add_access: START')
        log.ok('entity: %s' % self.id)
        log.ok('ddrfile: %s' % ddrfile)
        
        src_path = ddrfile.path_abs
        tmp_dir = os.path.join(
            MEDIA_BASE, 'tmp', 'file-add',
            self.parent_uid, self.id)
        dest_dir = self.files_path

        log.ok('Checking files/dirs')
        def check_dir(label, path, mkdir=False, perm=os.W_OK):
            log.ok('%s: %s' % (label, path))
            if mkdir and not os.path.exists(path):
                os.makedirs(path)
            if not os.path.exists(path): crash('%s does not exist' % label)
            if not os.access(path, perm): crash('%s not has permission %s' % (label, permission))
        check_dir('src_path', src_path, mkdir=False, perm=os.R_OK)
        check_dir('tmp_dir', tmp_dir, mkdir=True, perm=os.W_OK)
        check_dir('dest_dir', dest_dir, mkdir=True, perm=os.W_OK)
        
        log.ok('Making access file')
        access_filename = DDRLocalFile.access_filename(src_path)
        tmp_access_path = None
        try:
            tmp_access_path = imaging.thumbnail(
                src_path,
                os.path.join(tmp_dir, os.path.basename(access_filename)),
                geometry=ACCESS_FILE_GEOMETRY)
        except:
            # write traceback to log and continue on
            log.not_ok(traceback.format_exc().strip())
        if tmp_access_path and os.path.exists(tmp_access_path):
            log.ok('Attaching access file')
            #dest_access_path = os.path.join('files', os.path.basename(tmp_access_path))
            #log.ok('dest_access_path: %s' % dest_access_path)
            f.set_access(tmp_access_path, self)
            log.ok('f.access_rel: %s' % f.access_rel)
            log.ok('f.access_abs: %s' % f.access_abs)
        else:
            crash('Failed to make an access file from %s' % src_path)
        
        log.ok('Writing file metadata')
        tmp_file_json = os.path.join(tmp_dir, os.path.basename(f.json_path))
        log.ok(tmp_file_json)
        with open(tmp_file_json, 'w') as j:
            j.write(f.dump_json())
        if not os.path.exists(tmp_file_json):
            crash('Could not write file metadata %s' % tmp_file_json)
        
        # WE ARE NOW MAKING CHANGES TO THE REPO ------------------------
        
        log.ok('Moving files to dest_dir')
        new_files = []
        new_files.append([tmp_access_path, f.access_abs])
        mvfiles_failures = []
        for tmp,dest in new_files:
            log.ok('mv %s %s' % (tmp,dest))
            os.rename(tmp,dest)
            if not os.path.exists(dest):
                log.not_ok('FAIL')
                mvfiles_failures.append(tmp)
                break
        # one of new_files failed to copy, so move all back to tmp
        if mvfiles_failures:
            log.not_ok('%s failures: %s' % (len(mvfiles_failures), mvfiles_failures))
            log.not_ok('moving files back to tmp_dir')
            try:
                for tmp,dest in new_files:
                    log.ok('mv %s %s' % (dest,tmp))
                    os.rename(dest,tmp)
                    if not os.path.exists(tmp) and not os.path.exists(dest):
                        log.not_ok('FAIL')
            except:
                msg = "Unexpected error:", sys.exc_info()[0]
                log.not_ok(msg)
                raise
            finally:
                crash('Failed to place one or more files to destination repo')
        # file metadata will only be copied if everything else was moved
        log.ok('mv %s %s' % (tmp_file_json, f.json_path))
        os.rename(tmp_file_json, f.json_path)
        if not os.path.exists(f.json_path):
            crash('Failed to place file metadata in destination repo')
        
        # commit
        git_files = [f.json_path_rel]
        annex_files = [f.access_rel]
        log.ok('entity_annex_add(%s, %s, %s, %s, %s, %s, %s, %s)' % (
            git_name, git_mail,
            self.parent_path, self.id,
            git_files, annex_files,
            agent, self))
        try:
            exit,status = commands.entity_annex_add(
                git_name, git_mail,
                self.parent_path, self.id, git_files, annex_files,
                agent=agent, entity=self)
            log.ok('status: %s' % status)
            log.ok('ddrlocal.models.DDRLocalEntity.add_file: FINISHED')
        except:
            # COMMIT FAILED! try to pick up the pieces
            # print traceback to addfile log
            with open(self._addfile_log_path(), 'a') as f:
                traceback.print_exc(file=f)
            # mv files back to tmp_dir
            log.not_ok('status: %s' % status)
            log.not_ok('Cleaning up...')
            for tmp,dest in new_files:
                log.not_ok('mv %s %s' % (dest,tmp))
                os.rename(dest,tmp)
            # restore backup of original file metadata
            log.not_ok('cp %s %s' % (file_json_backup, f.json_path))
            shutil.copy(file_json_backup, f.json_path)
            log.not_ok('finished cleanup. good luck...')
            raise
        
        return f,repo,log
    
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
    id = 'whatever'
    # path relative to /
    # (ex: /var/www/media/base/ddr-testing-71/files/ddr-testing-71-6/files/ddr-testing-71-6-dd9ec4305d.jpg)
    # not saved; constructed on instantiation
    path = None
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
            self.id = '-'.join([self.repo,self.org,self.cid,self.eid,self.role,self.sha1])
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
            self.path = self.path_abs
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
            ## TODO seriously, do we need this?
            #with open(self.json_path, 'r') as f:
            #    self.load_json(f.read())
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
    
    def model_def_commits( self ):
        return cmp_model_definition_commits(self, filemodule)
    
    def model_def_fields( self ):
        with open(self.json_path, 'r') as f:
            text = f.read()
        return cmp_model_definition_fields(text, filemodule)
    
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
        """Apply display_{field} functions to prep object data for the UI.
        """
        return labels_values(self, filemodule)
    
    def form_prep(self):
        """Apply formprep_{field} functions to prep data dict to pass into DDRForm object.
        
        @returns data: dict object as used by Django Form object.
        """
        data = form_prep(self, filemodule)
        return data
    
    def form_post(self, form):
        """Apply formpost_{field} functions to process cleaned_data from DDRForm
        
        @param form: DDRForm object
        """
        form_post(self, filemodule, form)
    
    @staticmethod
    def from_json(file_json):
        """Creates a DDRLocalFile and populates with data from JSON file.
        
        @param file_json: Absolute path to JSON file.
        @returns: DDRLocalFile
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
            file_ = DDRLocalFile(path_abs=file_abs)
            with open(file_.json_path, 'r') as f:
                file_.load_json(f.read())
        return file_
    
    def load_json(self, json_text):
        """Populate File data from JSON-formatted text.
        
        @param json_text: JSON-formatted text
        """
        json_data = load_json(self, filemodule, json_text)
        # fill in the blanks
        if self.access_rel:
            access_abs = os.path.join(self.entity_files_path, self.access_rel)
            if os.path.exists(access_abs):
                self.access_abs = access_abs
    
    def dump_json(self, doc_metadata=False):
        """Dump File data to JSON-formatted text.
        
        @param doc_metadata: boolean. Insert document_metadata().
        @returns: JSON-formatted text
        """
        data = prep_json(self, filemodule)
        if doc_metadata:
            data.insert(0, document_metadata(filemodule, self.collection_path))
        data.insert(1, {'path_rel': self.path_rel})
        return format_json(data)

    def write_json(self):
        """Write JSON file to disk.
        """
        json_data = self.dump_json(doc_metadata=True)
        # TODO use codecs.open utf-8
        with open(self.json_path, 'w') as f:
            f.write(json_data)

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
            ACCESS_FILE_APPEND,
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
