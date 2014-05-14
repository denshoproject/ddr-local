from datetime import datetime, date
import hashlib
import json
import logging
logger = logging.getLogger(__name__)
import os
import re
from StringIO import StringIO
import sys

import envoy
import libxmp
from lxml import etree
from sorl.thumbnail import default

from django.conf import settings
from django.core.files import File
from django.core.urlresolvers import reverse

from DDR import commands
from DDR import dvcs
from DDR import natural_order_string
from DDR.models import Collection as DDRCollection, Entity as DDREntity
from ddrlocal import VERSION, git_commit
from ddrlocal.models import collection as collectionmodule
from ddrlocal.models import entity as entitymodule
from ddrlocal.models import files as filemodule
from ddrlocal.models.meta import CollectionJSON, EntityJSON, read_json
from ddrlocal.models.xml import EAD, METS



COLLECTION_FILES_PREFIX = 'files'
ENTITY_FILES_PREFIX = 'files'

def git_version(repo_path=None):
    """Returns version info for Git and git-annex.
    
    If repo_path is specified, returns version of local repo's annex.
    example:
    'git version 1.7.10.4; git-annex version: 3.20120629; local repository version: 3; ' \
    'default repository version: 3; supported repository versions: 3; ' \
    'upgrade supported from repository versions: 0 1 2'
    
    @param repo_path: Absolute path to repository (optional).
    @returns string
    """
    try:
        # git
        gitv = envoy.run('git --version').std_out.strip()
        # git annex
        if repo_path and os.path.exists(repo_path):
            os.chdir(repo_path)
        annex = envoy.run('git annex version').std_out.strip().split('\n')
        gitversion = '; '.join([gitv] + annex)
    except Exception as err:
        gitversion = '%s' % err
    return gitversion

def module_function(module, function_name, value):
    """If named function is present in module and callable, pass value to it and return result.
    
    Among other things this may be used to prep data for display, prepare it
    for editing in a form, or convert cleaned form data into Python data for
    storage in objects.
    
    @param module: A Python module
    @param function_name: Name of the function to be executed.
    @param value: A single value to be passed to the function, or None.
    @returns: Whatever the specified function returns.
    """
    if (function_name in dir(module)):
        function = getattr(module, function_name)
        value = function(value)
    return value

def module_xml_function(module, function_name, tree, NAMESPACES, f, value):
    """If module function is present and callable, pass value to it and return result.
    
    Same as module_function() but with XML we need to pass namespaces lists to
    the functions.
    Used in dump_ead(), dump_mets().
    
    @param module: A Python module
    @param function_name: Name of the function to be executed.
    @param tree: An lxml tree object.
    @param NAMESPACES: Dict of namespaces used in the XML document.
    @param f: Field dict (from MODEL_FIELDS).
    @param value: A single value to be passed to the function, or None.
    @returns: Whatever the specified function returns.
    """
    if (function_name in dir(module)):
        function = getattr(module, function_name)
        tree = function(tree, NAMESPACES, f, value)
    return tree

def write_json(data, path):
    """Write JSON using consistent formatting and sorting.
    
    For versioning and history to be useful we need data fields to be written
    in a format that is easy to edit by hand and in which values can be compared
    from one commit to the next.  This function prints JSON with nice spacing
    and indentation and with sorted keys, so fields will be in the same relative
    position across commits.
    
    >>> data = {'a':1, 'b':2}
    >>> path = '/tmp/ddrlocal.models.write_json.json'
    >>> write_json(data, path)
    >>> with open(path, 'r') as f:
    ...     print(f.readlines())
    ...
    ['{\n', '    "a": 1,\n', '    "b": 2\n', '}']
    """
    json_pretty = json.dumps(data, indent=4, separators=(',', ': '), sort_keys=True)
    with open(path, 'w') as f:
        f.write(json_pretty)

def _inheritable_fields( MODEL_FIELDS ):
    """Returns a list of fields that can inherit or grant values.
    
    Inheritable fields are marked 'inheritable':True in MODEL_FIELDS.
    
    @param MODEL_FIELDS
    @returns: list
    """
    inheritable = []
    for f in MODEL_FIELDS:
        if f.get('inheritable', None):
            inheritable.append(f['name'])
    return inheritable

def _inherit( parent, child ):
    """Set inheritable fields in child object with values from parent.
    
    @param parent: A webui.models.Collection or webui.models.Entity
    @param child: A webui.models.Entity or webui.models.File
    """
    for field in parent.inheritable_fields():
        if hasattr(parent, field) and hasattr(child, field):
            setattr(child, field, getattr(parent, field))



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
    
    def url( self ):
        """Returns relative URL in context of webui app.
        
        TODO Move to webui.models
        
        >>> c = DDRLocalCollection('/tmp/ddr-testing-123')
        >>> c.url()
        '/ui/ddr-testing-123/'
        """
        return reverse('webui-collection', args=[self.repo, self.org, self.cid])
    
    def cgit_url( self ):
        """Returns cgit URL for collection.
        
        TODO Move to webui.models
        
        >>> c = DDRLocalCollection('/tmp/ddr-testing-123')
        >>> c.cgit_url()
        'http://partner.densho.org/cgit/cgit.cgi/ddr-testing-123/'
        """
        return '{}/cgit.cgi/{}/'.format(settings.CGIT_URL, self.uid)

    @staticmethod
    def collection_path(request, repo, org, cid):
        """Returns absolute path to collection repo directory.
        
        TODO Move to webui.models
        
        >>> DDRLocalCollection.collection_path(None, 'ddr', 'testing', 123)
        '/var/www/media/base/ddr-testing-123'
        """
        return os.path.join(settings.MEDIA_BASE, '{}-{}-{}'.format(repo, org, cid))
    
    def repo_fetch( self ):
        """Fetch latest changes to collection repo from origin/master.
        """
        result = '-1'
        if os.path.exists(os.path.join(self.path, '.git')):
            result = commands.fetch(self.path)
        else:
            result = '%s is not a git repository' % self.path
        return result
    
    def repo_status( self ):
        """Get status of collection repo vis-a-vis origin/master.
        
        The repo_(synced,ahead,behind,diverged,conflicted) functions all use
        the result of this function so that git-status is only called once.
        """
        if not self._status and (os.path.exists(os.path.join(self.path, '.git'))):
            status = dvcs.repo_status(self.path, short=True)
            if status:
                self._status = status
        return self._status
    
    def repo_synced( self ):     return dvcs.synced(self.repo_status())
    def repo_ahead( self ):      return dvcs.ahead(self.repo_status())
    def repo_behind( self ):     return dvcs.behind(self.repo_status())
    def repo_diverged( self ):   return dvcs.diverged(self.repo_status())
    def repo_conflicted( self ): return dvcs.conflicted(self.repo_status())
    
    def repo_annex_status( self ):
        """Get annex status of collection repo.
        """
        if not self._astatus and (os.path.exists(os.path.join(self.path, '.git'))):
            astatus = commands.annex_status(self.path)
            if astatus:
                self._astatus = astatus
        return self._astatus
    
    def _lockfile( self ):
        """Returns absolute path to collection repo lockfile.
        
        Note that the actual file may or may not be present.
        
        >>> c = DDRLocalCollection('/tmp/ddr-testing-123')
        >>> c._lockfile()
        '/tmp/ddr-testing-123/lock'
        """
        return os.path.join(self.path, 'lock')
     
    def lock( self, task_id ):
        """Writes lockfile to collection dir; complains if can't.
        
        Celery tasks don't seem to know their own task_id, and there don't
        appear to be any handlers that can be called just *before* a task
        is fired. so it appears to be impossible for a task to lock itself.
        
        This method should(?) be called immediately after starting the task:
        >> result = collection_sync.apply_async((args...), countdown=2)
        >> lock_status = collection.lock(result.task_id)
        
        >>> path = '/tmp/ddr-testing-123'
        >>> os.mkdir(path)
        >>> c = DDRLocalCollection(path)
        >>> c.lock('abcdefg')
        'ok'
        >>> c.lock('abcdefg')
        'locked'
        >>> c.unlock('abcdefg')
        'ok'
        >>> os.rmdir(path)
        
        TODO return 0 if successful
        
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
        
        >>> path = '/tmp/ddr-testing-123'
        >>> os.mkdir(path)
        >>> c = DDRLocalCollection(path)
        >>> c.lock('abcdefg')
        'ok'
        >>> c.unlock('xyz')
        'task_id miss'
        >>> c.unlock('abcdefg')
        'ok'
        >>> c.unlock('abcdefg')
        'not locked'
        >>> os.rmdir(path)
        
        TODO return 0 if successful
        
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
        """Returns celery task_id if collection repo is locked, False if not
        
        >>> c = DDRLocalCollection('/tmp/ddr-testing-123')
        >>> c.locked()
        False
        >>> c.lock('abcdefg')
        'ok'
        >>> c.locked()
        'abcdefg'
        >>> c.unlock('abcdefg')
        'ok'
        >>> c.locked()
        False
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
    
    def entities( self ):
        """Returns list of the Collection's Entity objects.
        
        >>> c = Collection.from_json('/tmp/ddr-testing-123')
        >>> c.entities()
        [<DDRLocalEntity ddr-testing-123-1>, <DDRLocalEntity ddr-testing-123-2>, ...]
        """
        entities = []
        if os.path.exists(self.files_path):
            for eid in os.listdir(self.files_path):
                path = os.path.join(self.files_path, eid)
                entity = DDRLocalEntity.from_json(path)
                for lv in entity.labels_values():
                    if lv['label'] == 'title':
                        entity.title = lv['value']
                entities.append(entity)
        entities = sorted(entities, key=lambda e: natural_order_string(e.uid))
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
        
        @param path: [optional] Alternate file path.
        @param template: [optional] Boolean. If true, write default values for fields.
        """
        collection = [{'application': 'https://github.com/densho/ddr-local.git',
                       'commit': git_commit(),
                       'release': VERSION,
                       'git': git_version(self.path),}]
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
        _files = []
        try:
            for f in self.files:
                path_abs = os.path.join(self.files_path, f['path_rel'])
                _files.append(DDRLocalFile(path_abs))
        except:
            pass
        self.files = _files
    
    def dump_json(self, path=None, template=False):
        """Dump Entity data to .json file.
        
        @param path: [optional] Alternate file path.
        @param template: [optional] Boolean. If true, write default values for fields.
        """
        entity = [{'application': 'https://github.com/densho/ddr-local.git',
                   'commit': git_commit(),
                   'release': VERSION,
                   'git': git_version(self.parent_path),}]
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
            # NOTE: we get role from filename and also from JSON data, if available
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
    
    def dump_json(self):
        """Dump File data to .json file.
        @param path: Absolute path to .json file.
        """
        # TODO DUMP FILE AND FILEMETA PROPERLY!!!
        file_ = [{'application': 'https://github.com/densho/ddr-local.git',
                  'commit': git_commit(),
                  'release': VERSION,
                  'git': git_version(self.collection_path),},
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
            s = etree.tostring(tree, pretty_print=False).strip()
            while s.find('\n ') > -1:
                s = s.replace('\n ', '\n')
            s = s.replace('\n','')
            return s
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
