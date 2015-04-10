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

from DDR import commands
from DDR import docstore
from DDR import dvcs
from DDR.models import Identity
from DDR.models import Module
from DDR.models import read_json, write_json, from_json
from DDR.models import Collection as DDRCollection
from DDR.models import Entity as DDREntity
from DDR.models import File
from DDR.models import COLLECTION_FILES_PREFIX, ENTITY_FILES_PREFIX

if settings.REPO_MODELS_PATH not in sys.path:
    sys.path.append(settings.REPO_MODELS_PATH)
try:
    from repo_models import collection as collectionmodule
    from repo_models import entity as entitymodule
    from repo_models import files as filemodule
except ImportError:
    from DDR.models import collectionmodule
    from DDR.models import entitymodule
    from DDR.models import filemodule

from webui import gitstatus
from webui import WEBUI_MESSAGES
from webui import COLLECTION_FETCH_CACHE_KEY
from webui import COLLECTION_STATUS_CACHE_KEY
from webui import COLLECTION_ANNEX_STATUS_CACHE_KEY
from webui import COLLECTION_FETCH_TIMEOUT
from webui import COLLECTION_STATUS_TIMEOUT
from webui import COLLECTION_ANNEX_STATUS_TIMEOUT


def repo_models_valid(request):
    """Displays alerts if repo_models are absent or undefined
    
    Wrapper around DDR.models.Module.is_valid
    
    @param request
    @returns: boolean
    """
    valid = True
    NOIMPORT_MSG = 'Error: Could not import model definitions!'
    UNDEFINED_MSG = 'Error: One or more models improperly defined.'
    # don't check again if messages already added
    added = False
    for m in messages.get_messages(request):
        if (NOIMPORT_MSG in m.message) or (UNDEFINED_MSG in m.message):
            added = True
    if added:
        valid = False
    else:
        cvalid,cmsg = Module(collectionmodule).is_valid()
        evalid,emsg = Module(entitymodule).is_valid()
        fvalid,fmsg = Module(filemodule).is_valid()
        if not (cvalid and evalid and fvalid):
            valid = False
            messages.error(request, UNDEFINED_MSG)
    return valid

def model_def_commits(document, module):
    """
    Wrapper around DDR.models.model_def_commits
    
    @param document
    @param module
    """
    status = super(module, document).model_def_commits()
    alert,msg = WEBUI_MESSAGES['MODEL_DEF_COMMITS_STATUS_%s' % status]
    document.model_def_commits_alert = alert
    document.model_def_commits_msg = msg

def model_def_fields(document, module):
    """
    Wrapper around DDR.models.model_def_fields
    
    @param document
    @param module
    """
    added,removed = super(module, document).model_def_fields()
    # 'File.path_rel' is created when instantiating Files,
    # is not part of model definitions.
    def rm_path_rel(fields):
        if 'path_rel' in fields:
            fields.remove('path_rel')
    rm_path_rel(added)
    rm_path_rel(removed)
    document.model_def_fields_added = added
    document.model_def_fields_removed = removed
    document.model_def_fields_added_msg = WEBUI_MESSAGES['MODEL_DEF_FIELDS_ADDED'] % added
    document.model_def_fields_removed_msg = WEBUI_MESSAGES['MODEL_DEF_FIELDS_REMOVED'] % removed

def form_prep(document, module):
    """Apply formprep_{field} functions to prep data dict to pass into DDRForm object.
    
    Certain fields require special processing.  Data may need to be massaged
    and prepared for insertion into particular Django form objects.
    If a "formprep_{field}" function is present in the collectionmodule
    it will be executed.
    
    @param document: Collection, Entity, File document object
    @param module: collection, entity, files model definitions module
    @returns data: dict object as used by Django Form object.
    """
    data = {}
    for f in module.FIELDS:
        if hasattr(document, f['name']) and f.get('form',None):
            key = f['name']
            # run formprep_* functions on field data if present
            value = Module(module).function(
                'formprep_%s' % key,
                getattr(document, f['name'])
            )
            data[key] = value
    return data
    
def form_post(document, module, form):
    """Apply formpost_{field} functions to process cleaned_data from CollectionForm
    
    Certain fields require special processing.
    If a "formpost_{field}" function is present in the entitymodule
    it will be executed.
    
    @param document: Collection, Entity, File document object
    @param module: collection, entity, files model definitions module
    @param form: DDRForm object
    """
    for f in module.FIELDS:
        if hasattr(document, f['name']) and f.get('form',None):
            key = f['name']
            # run formpost_* functions on field data if present
            cleaned_data = Module(module).function(
                'formpost_%s' % key,
                form.cleaned_data[key]
            )
            setattr(document, key, cleaned_data)
    # update record_lastmod
    if hasattr(document, 'record_lastmod'):
        document.record_lastmod = datetime.now()

def post_json(hosts, index, json_path):
    """Post current .json to docstore.
    
    @param hosts: list of dicts containing host information.
    @param index: Name of the target index.
    @param json_path: Absolute path to .json file.
    @returns: JSON dict with status code and response
    """
    status = docstore.post(
        hosts, index,
        json.loads(read_json(json_path)),
        private_ok=True)
    logging.debug(str(status))
    return status


# functions relating to inheritance ------------------------------------



class Collection( DDRCollection ):
    
    def __repr__(self):
        """Returns string representation of object.
        """
        return "<webui.models.Collection %s>" % (self.id)
    
    @staticmethod
    def collection_path(request, repo, org, cid):
        """Returns absolute path to collection repo directory.
        
        >>> DDRLocalCollection.collection_path(None, 'ddr', 'testing', 123)
        '/var/www/media/base/ddr-testing-123'
        """
        return Identity.path_from_id(
            Identity.make_object_id('collection', repo, org, cid),
            settings.MEDIA_BASE
        )
    
    @staticmethod
    def from_id_parts(repo, org, cid):
        object_id = Identity.make_object_id('collection', repo, org, cid)
        path = Identity.path_from_id(object_id, settings.MEDIA_BASE)
        return Collection.from_json(path)
    
    @staticmethod
    def from_json(collection_abs):
        """Instantiates a Collection object, loads data from collection.json.
        
        @param collection_abs: Absolute path, without .json file.
        @returns: Collection
        """
        return from_json(
            Collection,
            Identity.json_path_from_dir('collection', collection_abs)
        )
    
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
    
    def model_def_commits(self):
        """Assesses document's relation to model defs in 'ddr' repo.
        
        Adds the following fields:
        .model_def_commits_alert
        .model_def_commits_msg
        """
        model_def_commits(self, Collection)
    
    def model_def_fields(self):
        """From POV of document, indicates fields added/removed in model defs
        
        Adds the following fields:
        .model_def_fields_added
        .model_def_fields_removed
        .model_def_fields_added_msg
        .model_def_fields_removed_msg
        """
        model_def_fields(self, Collection)
    
    def form_prep(self):
        """Apply formprep_{field} functions to prep data dict to pass into DDRForm object.
        
        @returns data: dict object as used by Django Form object.
        """
        return form_prep(self, collectionmodule)
    
    def form_post(self, form):
        """Apply formpost_{field} functions to process cleaned_data from DDRForm
        
        @param form: DDRForm object
        """
        form_post(self, collectionmodule, form)
    
    def post_json(self, hosts, index):
        return post_json(hosts, index, self.json_path)
    
    @staticmethod
    def create(collection_path, git_name, git_mail):
        """create new entity given an entity ID
        """
        # write collection.json template to collection location and commit
        write_json(Collection(collection_path).dump_json(template=True),
                   settings.TEMPLATE_CJSON)
        templates = [settings.TEMPLATE_CJSON, settings.TEMPLATE_EAD]
        agent = settings.AGENT
        
        exit,status = commands.create(
            git_name, git_mail, collection_path, templates, agent)
        
        collection = Collection.from_json(collection_path)
        
        # [delete cache], update search index
        #collection.cache_delete()
        with open(collection.json_path, 'r') as f:
            document = json.loads(f.read())
        docstore.post(settings.DOCSTORE_HOSTS, settings.DOCSTORE_INDEX, document)
        
        return collection
    
    def save( self, updated_files, git_name, git_mail ):
        """Perform file-save functions.
        
        Commit files, delete cache, update search index.
        These steps are to be called asynchronously from tasks.collection_edit.
        
        @param collection: Collection
        @param updated_files: list
        @param git_name: str
        @param git_mail: str
        """
        exit,status = commands.update(
            git_name, git_mail,
            self.path, updated_files,
            agent=settings.AGENT)
        self.cache_delete()
        with open(self.json_path, 'r') as f:
            document = json.loads(f.read())
        docstore.post(settings.DOCSTORE_HOSTS, settings.DOCSTORE_INDEX, document)
        return exit,status


class Entity( DDREntity ):
    
    def __repr__(self):
        """Returns string representation of object.
        """
        return "<webui.models.Entity %s>" % (self.id)
    
    @staticmethod
    def entity_path(request, repo, org, cid, eid):
        return Identity.path_from_id(
            Identity.make_object_id('entity', repo, org, cid, eid),
            settings.MEDIA_BASE
        )
    
    @staticmethod
    def from_id_parts(repo, org, cid, eid):
        object_id = Identity.make_object_id('entity', repo, org, cid, eid)
        path = Identity.path_from_id(object_id, settings.MEDIA_BASE)
        return Entity.from_json(path)
    
    @staticmethod
    def from_json(entity_abs):
        """
        @param entity_abs: Absolute path, without .json file.
        @returns: Entity
        """
        return from_json(
            Entity,
            Identity.json_path_from_dir('entity', entity_abs)
        )
    
    def url( self ):
        return reverse('webui-entity', args=[self.repo, self.org, self.cid, self.eid])
    
    def model_def_commits(self):
        """Assesses document's relation to model defs in 'ddr' repo.
        
        Adds the following fields:
        .model_def_commits_alert
        .model_def_commits_msg
        """
        model_def_commits(self, Entity)
    
    def model_def_fields(self):
        """From POV of document, indicates fields added/removed in model defs
        
        Adds the following fields:
        .model_def_fields_added
        .model_def_fields_removed
        .model_def_fields_added_msg
        .model_def_fields_removed_msg
        """
        model_def_fields(self, Entity)
    
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
    
    def post_json(self, hosts, index):
        return post_json(hosts, index, self.json_path)
    
    def load_file_objects( self ):
        """Replaces list of file info dicts with list of DDRFile objects
        
        Overrides the function in .models.DDRLocalEntity, which
        adds DDRLocalFile objects which are missing certain methods of
        DDRFile.
        """
        self._file_objects = []
        for f in self.files:
            if f and f.get('path_rel',None):
                path_abs = Identity.path_from_id(
                    Identity.id_from_path(f['path_rel']),
                    settings.MEDIA_BASE
                )
                file_ = DDRFile(path_abs=path_abs)
                file_.load_json(read_json(file_.json_path))
                self._file_objects.append(file_)
        # keep track of how many times this gets loaded...
        self._file_objects_loaded = self._file_objects_loaded + 1
    
    @staticmethod
    def create(collection, entity_id, git_name, git_mail, agent=settings.AGENT):
        """create new entity given an entity ID
        """
        repo,org,cid,eid = entity_id.split('-')
        entity_path = Entity.entity_path(None, repo, org, cid, eid)
        
        # write entity.json template to entity location and commit
        write_json(Entity(entity_path).dump_json(template=True),
                   settings.TEMPLATE_EJSON)
        exit,status = commands.entity_create(
            git_name, git_mail,
            collection.path, entity_id,
            [collection.json_path_rel, collection.ead_path_rel],
            [settings.TEMPLATE_EJSON, settings.TEMPLATE_METS],
            agent=agent)
        
        # load new entity, inherit values from parent, write and commit
        entity = Entity.from_json(entity_path)
        entity.inherit(collection)
        entity.dump_json()
        updated_files = [entity.json_path]
        exit,status = commands.entity_update(
            git_name, git_mail,
            collection.path, entity.id,
            updated_files,
            agent=agent)

        # delete cache, update search index
        collection.cache_delete()
        with open(entity.json_path, 'r') as f:
            document = json.loads(f.read())
        docstore.post(settings.DOCSTORE_HOSTS, settings.DOCSTORE_INDEX, document)
        
        return entity
        
    def save_part1( self, form ):
        """Save entity part 1: the fast parts
        
        Write changes to disk; propagate inheritable values to child objects.
        These steps are relatively quick, can be done during request-response.
        
        @param form: Django form object
        @returns: list of paths
        """
        # run module_functions on raw form data
        self.form_post(form)
        # write
        self.dump_json()
        self.dump_mets()
        updated_files = [self.json_path, self.mets_path,]
        inheritables = self.selected_inheritables(form.cleaned_data)
        modified_ids,modified_files = self.update_inheritables(inheritables, form.cleaned_data)
        if modified_files:
            updated_files = updated_files + modified_files
        return updated_files
    
    def save_part2( self, updated_files, collection, git_name, git_mail ):
        """Save entity part 2: the slow parts
        
        Commit files, delete cache, update search index.
        These steps are slow, should be called from tasks.entity_edit
        
        @param updated_files: list of paths
        @param collection: Collection
        @param git_name: str
        @param git_mail: str
        """
        exit,status = commands.entity_update(
            git_name, git_mail,
            collection.path, self.id,
            updated_files,
            agent=settings.AGENT)
        collection.cache_delete()
        with open(self.json_path, 'r') as f:
            document = json.loads(f.read())
        docstore.post(settings.DOCSTORE_HOSTS, settings.DOCSTORE_INDEX, document)
        return exit,status


class DDRFile( File ):
    
    def __repr__(self):
        """Returns string representation of object.
        """
        return "<webui.models.DDRFile %s>" % (self.id)
    
    @staticmethod
    def file_path(request, repo, org, cid, eid, role, sha1):
        return Identity.path_from_id(
            Identity.make_object_id('file', repo, org, cid, eid, role, sha1),
            settings.MEDIA_BASE
        )
    
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
    
    def model_def_commits(self):
        """Assesses document's relation to model defs in 'ddr' repo.
        
        Adds the following fields:
        .model_def_commits_alert
        .model_def_commits_msg
        """
        model_def_commits(self, DDRFile)
    
    def model_def_fields(self):
        """From POV of document, indicates fields added/removed in model defs
        
        Adds the following fields:
        .model_def_fields_added
        .model_def_fields_removed
        .model_def_fields_added_msg
        .model_def_fields_removed_msg
        """
        model_def_fields(self, DDRFile)
    
    def form_prep(self):
        """Apply formprep_{field} functions to prep data dict to pass into DDRForm object.
        
        @returns data: dict object as used by Django Form object.
        """
        return form_prep(self, filemodule)
    
    def form_post(self, form):
        """Apply formpost_{field} functions to process cleaned_data from DDRForm
        
        @param form: DDRForm object
        """
        form_post(self, filemodule, form)
    
    def post_json(self, hosts, index):
        return post_json(hosts, index, self.json_path)
    
    def save( self, git_name, git_mail ):
        """Perform file-save functions.
        
        Commit files, delete cache, update search index.
        These steps are to be called asynchronously from tasks.file_edit.
        
        @param collection: Collection
        @param file_id: str
        @param git_name: str
        @param git_mail: str
        """
        collection = Collection.from_json(self.collection_path)
        entity_id = Identity.make_object_id(
            'entity', self.repo, self.org, self.cid, self.eid)
        
        exit,status = commands.entity_update(
            git_name, git_mail,
            collection.path, entity_id,
            [self.json_path],
            agent=settings.AGENT)
        collection.cache_delete()
        with open(self.json_path, 'r') as f:
            document = json.loads(f.read())
        docstore.post(settings.DOCSTORE_HOSTS, settings.DOCSTORE_INDEX, document)
        
        return exit,status
