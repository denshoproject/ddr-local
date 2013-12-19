import logging
logger = logging.getLogger(__name__)
import os

import envoy

from django.conf import settings
from django.core.cache import cache
from django.db import models

from DDR import dvcs
from DDR import inventory
from DDR.models import Organization

from ddrlocal.models import DDRLocalCollection, DDRLocalEntity, DDRLocalFile
from ddrlocal.models import collection as collectionmodule
from ddrlocal.models import entity as entitymodule
from ddrlocal.models import files as filemodule

COLLECTION_FETCH_CACHE_KEY = 'webui:collection:%s:fetch'
COLLECTION_STATUS_CACHE_KEY = 'webui:collection:%s:status'
COLLECTION_ANNEX_STATUS_CACHE_KEY = 'webui:collection:%s:annex_status'
COLLECTION_ANNEX_WHEREIS_CACHE_KEY = 'webui:collection:%s:annex_whereis'
COLLECTION_ANNEX_MAP_CACHE_KEY = 'webui:collection:%s:annex_map'

COLLECTION_FETCH_TIMEOUT = 0
COLLECTION_STATUS_TIMEOUT = 60 * 10
COLLECTION_ANNEX_STATUS_TIMEOUT = 60 * 10
COLLECTION_ANNEX_WHEREIS_TIMEOUT = 60 * 10
COLLECTION_ANNEX_MAP_TIMEOUT = 60 * 10



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
    
    def cache_delete( self ):
        cache.delete(COLLECTION_FETCH_CACHE_KEY % self.id)
        cache.delete(COLLECTION_STATUS_CACHE_KEY % self.id)
        cache.delete(COLLECTION_ANNEX_STATUS_CACHE_KEY % self.id)
        cache.delete(COLLECTION_ANNEX_WHEREIS_CACHE_KEY % self.id)
        cache.delete(COLLECTION_ANNEX_MAP_CACHE_KEY % self.id)
    
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
    
    def repo_status( self ):
        key = COLLECTION_STATUS_CACHE_KEY % self.id
        data = cache.get(key)
        if not data:
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
    
    def repo_annex_whereis( self ):
        key = COLLECTION_ANNEX_WHEREIS_CACHE_KEY % self.id
        data = cache.get(key)
        if not data:
            org_path = os.path.join(settings.MEDIA_BASE, '%s-%s' % (self.repo, self.org))
            org = Organization.load(org_path)
            drive_label = inventory.guess_drive_label(self.path)
            repo = dvcs.repository(self.path)
            data = org.collection_whereis(drive_label, repo=repo)
            cache.set(key, data, COLLECTION_ANNEX_WHEREIS_TIMEOUT)
        return data
    
    def repo_annex_map( self ):
        key = COLLECTION_ANNEX_MAP_CACHE_KEY % self.id
        data = cache.get(key)
        if not data:
            repo = dvcs.repository(self.path)
            data = dvcs.annex_map(repo).replace(settings.MEDIA_BASE, '')[1:]
            cache.set(key, data, COLLECTION_ANNEX_MAP_TIMEOUT)
        return data
    
    def selected_inheritables(self, cleaned_data ):
        return _selected_inheritables(self.inheritable_fields(), cleaned_data)
    
    def update_inheritables( self, inheritables, cleaned_data ):
        return _update_inheritables(self, 'collection', inheritables, cleaned_data)



class Entity( DDRLocalEntity ):
    
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
