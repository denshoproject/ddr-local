from datetime import datetime
import json
import logging
logger = logging.getLogger(__name__)
import os
import sys

import envoy
import requests

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.db import models

from DDR import dvcs
from DDR.storage import storage_status

from storage import base_path

from ddrlocal.models import DDRLocalCollection, DDRLocalEntity, DDRLocalFile
from ddrlocal.models import COLLECTION_FILES_PREFIX, ENTITY_FILES_PREFIX

if settings.REPO_MODELS_PATH not in sys.path:
    sys.path.append(settings.REPO_MODELS_PATH)
try:
    from repo_models import collection as collectionmodule
    from repo_models import entity as entitymodule
    from repo_models import files as filemodule
except ImportError:
    from ddrlocal.models import collection as collectionmodule
    from ddrlocal.models import entity as entitymodule
    from ddrlocal.models import files as filemodule

from webui import gitstatus

from webui import COLLECTION_FETCH_CACHE_KEY
from webui import COLLECTION_STATUS_CACHE_KEY
from webui import COLLECTION_ANNEX_STATUS_CACHE_KEY
from webui import COLLECTION_FETCH_TIMEOUT
from webui import COLLECTION_STATUS_TIMEOUT
from webui import COLLECTION_ANNEX_STATUS_TIMEOUT


def check_repo_models(request):
    """Displays alerts if repo_models are absent or undefined
    """
    NOIMPORT_MSG = 'Error: Could not import model definitions!'
    UNDEFINED_MSG = 'Error: One or more models are undefined!'
    # don't check again if messages already added
    added = False
    for m in messages.get_messages(request):
        if (NOIMPORT_MSG in m.message) or (UNDEFINED_MSG in m.message):
            added = True
    if not added:
        # ddr repo not available or doesn't contain repo_models
        if not 'ddr/repo_models' in collectionmodule.__file__:
            # collection.__file__ == absolute path to the module
            messages.error(request, NOIMPORT_MSG)
        # repo_models may be present but no models defined
        undefined = []
        if (not collectionmodule.COLLECTION_FIELDS):
            undefined.append('Collection')
        if (not entitymodule.ENTITY_FIELDS):
            undefined.append('Entity')
        if (not filemodule.FILE_FIELDS):
            undefined.append('File')
        if undefined:
            models = ', '.join(undefined)
            messages.error(request, UNDEFINED_MSG + ' [%s]' % models)



# functions relating to inheritance ------------------------------------

def _child_jsons( path ):
    """List all the .json files under path directory; excludes specified dir.
    
    @param path: Absolute directory path.
    @return list of paths
    """
    paths = []
    r = envoy.run('find %s -name "*.json" ! -name ".git" -print' % path)
    if not r.status_code:
        for p in r.std_out.strip().split('\n'):
            if os.path.dirname(p) != path:
                paths.append(p)
    return paths

def _selected_inheritables( inheritables, cleaned_data ):
    """Indicates which inheritable fields from the list were selected in the form.
    
    Selector fields are assumed to be BooleanFields named "FIELD_inherit".
    
    @param inheritables: List of field/attribute names.
    @param cleaned_data: form.cleaned_data.
    @return
    """
    fieldnames = {}
    for field in inheritables:
        fieldnames['%s_inherit' % field] = field
    selected = []
    if fieldnames:
        for key in cleaned_data.keys():
            if (key in fieldnames.keys()) and cleaned_data[key]:
                selected.append(fieldnames[key])
    return selected

def _selected_field_values( parent_object, inheritables ):
    """Gets list of selected inherited fieldnames and their values from the parent object
    
    @param parent_object
    @param inheritables
    """
    field_values = []
    for field in inheritables:
        value = getattr(parent_object, field)
        field_values.append( (field,value) )
    return field_values

def _load_object( json_path ):
    """Loads File, Entity, or Collection from JSON file
    
    @param json_path
    """
    dirname = os.path.dirname(json_path)
    basename = os.path.basename(json_path)
    if ('master' in basename) or ('mezzanine' in basename):  # file
        entity = Entity.from_json(os.path.dirname(dirname))
        fname = os.path.splitext(basename)[0]
        repo,org,cid,eid,role,sha1 = fname.split('-')
        return entity.file(repo, org, cid, eid, role, sha1)
    elif basename == 'entity.json':
        return Entity.from_json(dirname)
    elif basename == 'collection.json':
        return Collection.from_json(dirname)
    return None
    
def _update_inheritables( parent_object, objecttype, inheritables, cleaned_data ):
    """Update specified inheritable fields of child objects using form data.
    
    @param parent_object: A Collection, Entity, or File
    @param cleaned_data: Form cleaned_data from POST.
    @returns: tuple containing list of changed object Ids and list of changed objects' JSON files.
    """
    child_ids = []
    changed_files = []
    # values of selected inheritable fields from parent
    field_values = _selected_field_values(parent_object, inheritables)
    # load child objects and apply the change
    if field_values:
        for child_json in _child_jsons(parent_object.path):
            child = _load_object(child_json)
            if child:
                # set field if exists in child and doesn't already match parent value
                changed = False
                for field,value in field_values:
                    if hasattr(child, field):
                        existing_value = getattr(child,field)
                        if existing_value != value:
                            setattr(child, field, value)
                            changed = True
                # write json and add to list of changed IDs/files
                if changed:
                    child.dump_json()
                    if hasattr(child, 'id'):         child_ids.append(child.id)
                    elif hasattr(child, 'basename'): child_ids.append(child.basename)
                    changed_files.append(child_json)
    return child_ids,changed_files



class Collection( DDRLocalCollection ):
    
    @staticmethod
    def collection_path(request, repo, org, cid):
        """Returns absolute path to collection repo directory.
        
        >>> DDRLocalCollection.collection_path(None, 'ddr', 'testing', 123)
        '/var/www/media/base/ddr-testing-123'
        """
        return os.path.join(settings.MEDIA_BASE, '{}-{}-{}'.format(repo, org, cid))
    
    def gitstatus_path( self ):
        """Returns absolute path to collection .gitstatus cache file.
        
        >>> DDRLocalCollection.collection_path(None, 'ddr', 'testing', 123)
        '/var/www/media/base/ddr-test-123/.gitstatus'
        """
        return gitstatus.path(self.path)
    
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
    
    def cache_delete( self ):
        cache.delete(COLLECTION_FETCH_CACHE_KEY % self.id)
        cache.delete(COLLECTION_STATUS_CACHE_KEY % self.id)
        cache.delete(COLLECTION_ANNEX_STATUS_CACHE_KEY % self.id)
    
    @staticmethod
    def from_json(collection_abs):
        """Instantiates a Collection object, loads data from collection.json.
        """
        collection = Collection(collection_abs)
        collection_uid = collection.id  # save this just in case
        collection.load_json(collection.json_path)
        if not collection.id:
            # id gets overwritten if collection.json is blank
            collection.id = collection_uid
        return collection
    
    def repo_fetch( self ):
        key = COLLECTION_FETCH_CACHE_KEY % self.id
        data = cache.get(key)
        if not data:
            data = super(Collection, self).repo_fetch()
            cache.set(key, data, COLLECTION_FETCH_TIMEOUT)
        return data
    
    def repo_status( self, force=False ):
        key = COLLECTION_STATUS_CACHE_KEY % self.id
        data = cache.get(key)
        if force or (not data):
            data = super(Collection, self).repo_status()
            cache.set(key, data, COLLECTION_STATUS_TIMEOUT)
        return data
    
    def repo_annex_status( self ):
        key = COLLECTION_ANNEX_STATUS_CACHE_KEY % self.id
        data = cache.get(key)
        if not data:
            data = super(Collection, self).repo_annex_status()
            cache.set(key, data, COLLECTION_ANNEX_STATUS_TIMEOUT)
        return data
    
    def _repo_state( self, function_name ):
        """Use Collection.gitstatus if present (faster)
        
        Collection.repo_FUNCTION() required a git-status call so status
        could be passed to dvcs.FUNCTION().  These functions are called
        in collection base template and thus on pretty much every page.
        If Collection.gitstatus() is available it's a lot faster.
        """
        gs = gitstatus.read(settings.MEDIA_BASE, self.path)
        if gs and gs.get('status',None):
            if   function_name == 'synced': return dvcs.synced(gs['status'])
            elif function_name == 'ahead': return dvcs.ahead(gs['status'])
            elif function_name == 'behind': return dvcs.behind(gs['status'])
            elif function_name == 'diverged': return dvcs.diverged(gs['status'])
            elif function_name == 'conflicted': return dvcs.conflicted(gs['status'])
        else:
            if   function_name == 'synced': return super(Collection, self).repo_synced()
            elif function_name == 'ahead': return super(Collection, self).repo_ahead()
            elif function_name == 'behind': return super(Collection, self).repo_behind()
            elif function_name == 'diverged': return super(Collection, self).repo_diverged()
            elif function_name == 'conflicted': return super(Collection, self).repo_conflicted()
        return None

    def repo_synced( self ): return self._repo_state('synced')
    def repo_ahead( self ): return self._repo_state('ahead')
    def repo_behind( self ): return self._repo_state('behind')
    def repo_diverged( self ): return self._repo_state('diverged')
    def repo_conflicted( self ): return self._repo_state('conflicted')
        
    def sync_status( self, git_status, timestamp, cache_set=False, force=False ):
        return gitstatus.sync_status( self, git_status, timestamp, cache_set, force )
    
    def sync_status_url( self ):
        return reverse('webui-collection-sync-status-ajax',args=(self.repo,self.org,self.cid))
    
    def gitstatus( self, force=False ):
        return gitstatus.read(settings.MEDIA_BASE, self.path)

    def selected_inheritables(self, cleaned_data ):
        return _selected_inheritables(self.inheritable_fields(), cleaned_data)
    
    def update_inheritables( self, inheritables, cleaned_data ):
        return _update_inheritables(self, 'collection', inheritables, cleaned_data)



class Entity( DDRLocalEntity ):

    @staticmethod
    def entity_path(request, repo, org, cid, eid):
        collection_uid = '{}-{}-{}'.format(repo, org, cid)
        entity_uid     = '{}-{}-{}-{}'.format(repo, org, cid, eid)
        collection_abs = os.path.join(settings.MEDIA_BASE, collection_uid)
        entity_abs     = os.path.join(collection_abs, COLLECTION_FILES_PREFIX, entity_uid)
        return entity_abs
    
    def url( self ):
        return reverse('webui-entity', args=[self.repo, self.org, self.cid, self.eid])
    
    @staticmethod
    def from_json(entity_abs):
        entity = None
        if os.path.exists(entity_abs):
            entity = Entity(entity_abs)
            entity_uid = entity.id
            entity.load_json(entity.json_path)
            if not entity.id:
                entity.id = entity_uid  # might get overwritten if entity.json is blank
        return entity
    
    def selected_inheritables(self, cleaned_data ):
        return _selected_inheritables(self.inheritable_fields(), cleaned_data)
    
    def update_inheritables( self, inheritables, cleaned_data ):
        return _update_inheritables(self, 'entity', inheritables, cleaned_data)
    
    def _load_file_objects( self ):
        """Replaces list of file info dicts with list of DDRFile objects
        
        Overrides the function in ddrlocal.models.DDRLocalEntity, which
        adds DDRLocalFile objects which are missing certain methods of
        DDRFile.
        """
        # keep copy of the list for detect_file_duplicates()
        self._files = [f for f in self.files]
        self.files = []
        for f in self._files:
            path_abs = os.path.join(self.files_path, f['path_rel'])
            self.files.append(DDRFile(path_abs=path_abs))



class DDRFile( DDRLocalFile ):
    
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
