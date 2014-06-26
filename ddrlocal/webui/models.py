from datetime import datetime
import json
import logging
logger = logging.getLogger(__name__)
import os

import envoy
import requests

from django.conf import settings
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.db import models

from DDR import dvcs

from ddrlocal.models import DDRLocalCollection, DDRLocalEntity, DDRLocalFile
from ddrlocal.models import COLLECTION_FILES_PREFIX, ENTITY_FILES_PREFIX
from ddrlocal.models import collection as collectionmodule
from ddrlocal.models import entity as entitymodule
from ddrlocal.models import files as filemodule

COLLECTION_FETCH_CACHE_KEY = 'webui:collection:%s:fetch'
COLLECTION_STATUS_CACHE_KEY = 'webui:collection:%s:status'
COLLECTION_ANNEX_STATUS_CACHE_KEY = 'webui:collection:%s:annex_status'

COLLECTION_FETCH_TIMEOUT = 0
COLLECTION_STATUS_TIMEOUT = 60 * 10
COLLECTION_ANNEX_STATUS_TIMEOUT = 60 * 10



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

COLLECTION_SYNC_STATUS_CACHE_KEY = 'webui:collection:%s:sync-status'

def _sync_status( collection, git_status, cache_set=False, force=False ):
    """Cache collection repo sync status info for collections list page.
    Used in both .collections() and .sync_status_ajax().
    
    @param collection: 
    @param cache_set: Run git-status if data is not cached
    """
    key = COLLECTION_SYNC_STATUS_CACHE_KEY % collection.id
    data = cache.get(key)
    if force or (not data and cache_set):
        status = 'unknown'
        btn = 'muted'
        if   dvcs.ahead(git_status): status = 'ahead'; btn = 'warning'
        elif dvcs.behind(git_status): status = 'behind'; btn = 'warning'
        elif dvcs.conflicted(git_status): status = 'conflicted'; btn = 'danger'
        elif dvcs.synced(git_status): status = 'synced'; btn = 'success'
        elif collection.locked(): status = 'locked'; btn = 'warning'
        data = {
            'row': '#%s' % collection.id,
            'color': btn,
            'cell': '#%s td.status' % collection.id,
            'status': status,
        }
        cache.set(key, data, COLLECTION_STATUS_TIMEOUT)
    return data
    
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


def gitstatus_path( collection_path ):
    return os.path.join(collection_path, '.gitstatus')

def gitstatus_format( timestamp, elapsed, status, annex_status, sync_status ):
    """Formats git-status,git-annex-status,sync-status and timestamp
    
    Sample:
        {timestamp} {elapsed}
        %%
        {status}
        %%
        {annex status}
        %%
        {sync status}
    """
    timestamp_elapsed = ' '.join([
        timestamp.strftime(settings.TIMESTAMP_FORMAT),
        str(elapsed)
    ])
    return '\n%%\n'.join([
        timestamp_elapsed,
        status,
        annex_status,
        sync_status,
    ])

def gitstatus_parse( text ):
    """
    @returns: timestamp,elapsed,status,annex_status,sync_status
    """
    # we don't know in advance how many fields exist in .gitstatus
    # so get as many as we can
    variables = [None,None,None,None]
    for n,part in enumerate(text.split('%%')):
        variables[n] = part.strip()
    meta = variables[0]
    if meta:
        ts,elapsed = meta.split(' ')
        timestamp = datetime.strptime(ts, settings.TIMESTAMP_FORMAT)
    status = variables[1]
    annex_status = variables[2]
    sync_status = variables[3]
    return [timestamp, elapsed, status, annex_status, sync_status,]

def gitstatus_write( collection_path, timestamp, elapsed, status, annex_status, sync_status ):
    """Writes .gitstatus for the collection; see gitstatus_format.
    """
    text = gitstatus_format(timestamp, elapsed, status, annex_status, sync_status) + '\n'
    with open(gitstatus_path(collection_path), 'w') as f:
        f.write(text)
    return text

def gitstatus_read( collection_path ):
    """Reads .gitstatus for the collection and returns parsed data.
    """
    path = gitstatus_path(collection_path)
    if os.path.exists(path):
        with open(path, 'r') as f:
            text = f.read()
        return gitstatus_parse(text)
    return None




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
        return gitstatus_path(self.path)
    
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
    
    def repo_conflicted( self ):
        conflicted = False
        # try the quick way first
        gitstatus = self.gitstatus()
        if gitstatus and gitstatus.get('status',None):
            if dvcs.conflicted(gitstatus['status']):
                conflicted = True
        # the old slow way
        else:
            conflicted = super(Collection, self).repo_conflicted()
        return conflicted
        
    def sync_status( self, git_status, cache_set=False, force=False ):
        return _sync_status( self, git_status, cache_set, force )
    
    def sync_status_url( self ):
        return reverse('webui-collection-sync-status-ajax',args=(self.repo,self.org,self.cid))
    
    def gitstatus( self, force=False ):
        """Gets a bunch of status info for the collection; refreshes if forced
        
        timestamp, elapsed, status, annex_status, sync_status
        
        @param force: Boolean Forces refresh of status
        @returns: dict
        """
        timestamp=None; elapsed=None; status=None; annex_status=None; sync_status=None
        if os.path.exists(gitstatus_path(self.path)) and not force:
            timestamp,elapsed,status,annex_status,sync_status = gitstatus_read(self.path)
        elif force:
            start = datetime.now()
            status = super(Collection, self).repo_status()
            annex_status = super(Collection, self).repo_annex_status()
            sync_status = self.sync_status(git_status=status, force=True)
            timestamp = datetime.now()
            elapsed = timestamp - start
            text = gitstatus_write(self.path, timestamp, elapsed, status, annex_status, json.dumps(sync_status))
            timestamp,elapsed,status,annex_status,sync_status = gitstatus_parse(text)
        return {
            'timestamp': timestamp,
            'elapsed': elapsed,
            'status': status,
            'annex_status': annex_status,
            'sync_status': sync_status,
        }

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
        try:
            self.files = []
            for f in self._files:
                path_abs = os.path.join(self.files_path, f['path_rel'])
                self.files.append(DDRFile(path_abs))
        except:
            pass



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
