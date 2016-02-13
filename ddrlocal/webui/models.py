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
from DDR import fileio
from DDR import modules
from DDR.models import from_json
from DDR.models import Stub as DDRStub
from DDR.models import Collection as DDRCollection
from DDR.models import Entity as DDREntity
from DDR.models import File
from DDR.models import COLLECTION_FILES_PREFIX, ENTITY_FILES_PREFIX

from webui import gitstatus
from webui import WEBUI_MESSAGES
from webui import COLLECTION_FETCH_CACHE_KEY
from webui import COLLECTION_STATUS_CACHE_KEY
from webui import COLLECTION_ANNEX_STATUS_CACHE_KEY
from webui import COLLECTION_FETCH_TIMEOUT
from webui import COLLECTION_STATUS_TIMEOUT
from webui import COLLECTION_ANNEX_STATUS_TIMEOUT
from webui.identifier import Identifier, MODULES

# TODO get roles from somewhere (Identifier?)
FILE_ROLES = ['master', 'mezzanine',]


def repo_models_valid(request):
    """Displays alerts if repo_models are absent or undefined
    
    Wrapper around DDR.modules.Module.is_valid
    
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
        valid_modules = [
            modules.Module(module).is_valid()
            for model,module in MODULES.iteritems()
        ]
        if not (valid_modules):
            valid = False
            messages.error(request, UNDEFINED_MSG)
    return valid

def model_def_commits(document):
    """
    Wrapper around DDR.models.model_def_commits
    
    @param document: Collection, Entity, DDRFile
    """
    module = modules.Module(document.identifier.fields_module())
    document_commit = module.document_commit(document)
    module_commit = module.module_commit()
    if document_commit and module_commit:
        result = module.cmp_model_definition_commits(
            document_commit,
            module_commit
        )
        op = result['op']
    elif document_commit and not module_commit:
        op = '-m'
    elif module_commit and not document_commit:
        op = '-d'
    else:
        op = '--'
    alert,msg = WEBUI_MESSAGES['MODEL_DEF_COMMITS_STATUS_%s' % op]
    document.model_def_commits_alert = alert
    document.model_def_commits_msg = msg

def model_def_fields(document):
    """
    Wrapper around DDR.models.model_def_fields
    """
    module = document.identifier.fields_module()
    json_text = fileio.read_text(document.json_path)
    result = modules.Module(module).cmp_model_definition_fields(json_text)
    added = result['added']
    removed = result['removed']
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
            value = modules.Module(module).function(
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
            cleaned_data = modules.Module(module).function(
                'formpost_%s' % key,
                form.cleaned_data[key]
            )
            setattr(document, key, cleaned_data)
    # update record_lastmod
    if hasattr(document, 'record_lastmod'):
        document.record_lastmod = datetime.now()


# functions relating to inheritance ------------------------------------


class Stub(DDRStub):

    def parent(self, stubs=False):
        return self.identifier.parent(stubs).object()

class Collection( DDRCollection ):
    
    @staticmethod
    def from_json(path_abs, identifier=None):
        """Instantiates a Collection object from specified collection.json.
        
        @param path_abs: Absolute path to .json file.
        @param identifier: [optional] Identifier
        @returns: Collection
        """
        return from_json(Collection, path_abs, identifier)
    
    @staticmethod
    def from_identifier(identifier):
        """Instantiates a Collection object using data from Identidier.
        
        @param identifier: Identifier
        @returns: Collection
        """
        return from_json(Collection, identifier.path_abs('json'), identifier)
    
    @staticmethod
    def from_request(request):
        """Instantiates a Collection object using django.http.HttpRequest.
        
        @param request: Request
        @returns: Collection
        """
        return Collection.from_identifier(Identifier(request))

    def parent(self):
        return None
    
    def children(self, quick=None):
        """Returns list of the Collection's Entity objects.
        @param quick: Boolean List only titles and IDs
        """
        objects = super(Collection, self).children(quick=quick)
        for o in objects:
            oid = Identifier(id=o.id)
            o.absolute_url = reverse('webui-entity', args=oid.parts.values())
        return objects
    
    def gitstatus_path( self ):
        """Returns absolute path to collection .gitstatus cache file.
        
        >>> DDRLocalCollection.collection_path(None, 'ddr', 'testing', 123)
        '/var/www/media/base/ddr-test-123/.gitstatus'
        """
        return gitstatus.path(self.path)
    
    def absolute_url( self ):
        """Returns relative URL in context of webui app.
        
        TODO Move to webui.models
        
        >>> c = DDRLocalCollection('/tmp/ddr-testing-123')
        >>> c.absolute_url()
        '/ui/ddr-testing-123/'
        """
        return reverse('webui-collection', args=self.idparts)
    
    def admin_url(self): return reverse('webui-collection-admin', args=self.idparts)
    def changelog_url(self): return reverse('webui-collection-changelog', args=self.idparts)
    def children_url(self): return reverse('webui-collection-children', args=self.idparts)
    def ead_xml_url(self): return reverse('webui-collection-ead-xml', args=self.idparts)
    def edit_url(self): return reverse('webui-collection-edit', args=self.idparts)
    def export_entities_url(self): return reverse('webui-collection-export-entities', args=self.idparts)
    def export_files_url(self): return reverse('webui-collection-export-files', args=self.idparts)
    def git_status_url(self): return reverse('webui-collection-git-status', args=self.idparts)
    def json_url(self): return reverse('webui-collection-json', args=self.idparts)
    def merge_url(self): return reverse('webui-merge-raw', args=self.idparts)
    def new_entity_url(self): return reverse('webui-entity-new', args=self.idparts)
    def sync_url(self): return reverse('webui-collection-sync', args=self.idparts)
    
    def cgit_url( self ):
        """Returns cgit URL for collection.
        
        TODO Move to webui.models
        
        >>> c = DDRLocalCollection('/tmp/ddr-testing-123')
        >>> c.cgit_url()
        'http://partner.densho.org/cgit/cgit.cgi/ddr-testing-123/'
        """
        return '{}/cgit.cgi/{}/'.format(settings.CGIT_URL, self.id)
    
    def fs_url( self ):
        """URL of the collection directory browsable via Nginx.
        """
        return settings.MEDIA_URL + self.path.replace(settings.MEDIA_ROOT, '')
    
    def gitweb_url( self ):
        """Returns local gitweb URL for collection directory.
        """
        return '%s/?p=%s/.git;a=tree' % (settings.GITWEB_URL, self.id)
    
    def unlock_url(self, unlock_task_id):
        if unlock_task_id:
            args = [a for a in self.idparts]
            args.append(unlock_task_id)
            return reverse('webui-collection-unlock', args=args)
        return None
        
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
    
    def repo_states( self ):
        """Get collection's repo state from git-status if available
        """
        if not self._states:
            gs = gitstatus.read(settings.MEDIA_BASE, self.path)
            if gs and gs.get('status',None):
                self._states = dvcs.repo_states(gs['status'])
            else:
                self._states = dvcs.repo_states(self.repo_status())
        return self._states
        
    def sync_status( self, git_status, timestamp, cache_set=False, force=False ):
        return gitstatus.sync_status( self, git_status, timestamp, cache_set, force )
    
    def sync_status_url( self ):
        return reverse('webui-collection-sync-status-ajax', args=self.idparts)
    
    def gitstatus( self, force=False ):
        return gitstatus.read(settings.MEDIA_BASE, self.path)
    
    def model_def_commits(self):
        """Assesses document's relation to model defs in 'ddr' repo.
        
        Adds the following fields:
        .model_def_commits_alert
        .model_def_commits_msg
        """
        return model_def_commits(self)
    
    def model_def_fields(self):
        """From POV of document, indicates fields added/removed in model defs
        
        Adds the following fields:
        .model_def_fields_added
        .model_def_fields_removed
        .model_def_fields_added_msg
        .model_def_fields_removed_msg
        """
        model_def_fields(self)
    
    def form_prep(self):
        """Apply formprep_{field} functions to prep data dict to pass into DDRForm object.
        
        @returns data: dict object as used by Django Form object.
        """
        return form_prep(self, self.identifier.fields_module())
    
    def form_post(self, form):
        """Apply formpost_{field} functions to process cleaned_data from DDRForm
        
        @param form: DDRForm object
        """
        form_post(self, self.identifier.fields_module(), form)
    
    @staticmethod
    def create(collection_path, git_name, git_mail):
        """create new entity given an entity ID
        TODO remove write and commit, just create object
        """
        # write collection.json template to collection location and commit
        fileio.write_text(Collection(collection_path).dump_json(template=True),
                   settings.TEMPLATE_CJSON)
        templates = [settings.TEMPLATE_CJSON, settings.TEMPLATE_EAD]
        agent = settings.AGENT

        cidentifier = Identifier(collection_path)
        exit,status = commands.create(
            git_name, git_mail, cidentifier, templates, agent
        )
        
        collection = Collection.from_identifier(cidentifier)
        
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
            self, updated_files,
            agent=settings.AGENT)
        self.cache_delete()
        with open(self.json_path, 'r') as f:
            document = json.loads(f.read())
        docstore.post(settings.DOCSTORE_HOSTS, settings.DOCSTORE_INDEX, document)
        return exit,status


class Entity( DDREntity ):
    
    @staticmethod
    def from_json(path_abs, identifier=None):
        """Instantiates an Entity object from specified entity.json.
        
        @param path_abs: Absolute path to .json file.
        @param identifier: [optional] Identifier
        @returns: Entity
        """
        return from_json(Entity, path_abs, identifier)
    
    @staticmethod
    def from_identifier(identifier):
        """Instantiates an Entity object, loads data from entity.json.
        
        @param identifier: Identifier
        @returns: Entity
        """
        return from_json(Entity, identifier.path_abs('json'), identifier)
    
    @staticmethod
    def from_request(request):
        """Instantiates an Entity object using django.http.HttpRequest.
        
        @param request: Request
        @returns: Entity
        """
        return Entity.from_identifier(Identifier(request))
    
    def collection(self):
        return Collection.from_identifier(self.identifier.collection())
    
#    def parent(self):
#        return Collection.from_identifier(self.identifier.parent())

#    def children(self, role=None, quiet=None):
#        return []
    
    def absolute_url( self ):
        return reverse('webui-entity', args=self.idparts)
    
    def addfilelog_url(self): return reverse('webui-entity-addfilelog', args=self.idparts)
    def changelog_url(self): return reverse('webui-entity-changelog', args=self.idparts)
    def delete_url(self): return reverse('webui-entity-delete', args=self.idparts)
    def edit_url(self): return reverse('webui-entity-edit', args=self.idparts)
    def edit_json_url(self): return reverse('webui-entity-edit-json', args=self.idparts)
    def json_url(self): return reverse('webui-entity-json', args=self.idparts)
    def mets_xml_url(self): return reverse('webui-entity-mets-xml', args=self.idparts)
    
    def new_file_url(self, role):
        args = [a for a in self.idparts]
        args.append(role)
        return reverse('webui-file-new', args=args)
    
    def children_url(self, role):
        args = [a for a in self.idparts]
        args.append(role)
        return reverse('webui-file-role', args=args)
    
    def file_batch_url(self, role):
        args = [a for a in self.idparts]
        args.append(role)
        return reverse('webui-file-batch', args=args)
    
    def file_browse_url(self, role):
        args = [a for a in self.idparts]
        args.append(role)
        return reverse('webui-file-browse', args=args)
    
    def children_urls(self, active=None):
        return [
            {'url': self.children_url(role), 'name': role, 'active': role == active}
            for role in FILE_ROLES
        ]
    
    def file_batch_urls(self, active=None):
        return [
            {'url': self.file_batch_url(role), 'name': role, 'active': role == active}
            for role in FILE_ROLES
        ]
    
    def file_browse_urls(self, active=None):
        return [
            {'url': self.file_browse_url(role), 'name': role, 'active': role == active}
            for role in FILE_ROLES
        ]
    
    def fs_url( self ):
        """URL of the entity directory browsable via Nginx.
        """
        return settings.MEDIA_URL + os.path.dirname(self.json_path).replace(settings.MEDIA_ROOT, '')
    
    def gitweb_url( self ):
        """Returns local gitweb URL for entity directory.
        """
        return '%s/?p=%s/.git;a=tree;f=%s;hb=HEAD' % (
            settings.GITWEB_URL,
            self.parent_id,
            os.path.dirname(self.json_path_rel)
        )
    
    def unlock_url(self, unlock_task_id):
        if unlock_task_id:
            args = [a for a in self.idparts]
            args.append(unlock_task_id)
            return reverse('webui-entity-unlock', args=args)
        return None
    
    def model_def_commits(self):
        """Assesses document's relation to model defs in 'ddr' repo.
        
        Adds the following fields:
        .model_def_commits_alert
        .model_def_commits_msg
        """
        return model_def_commits(self)
    
    def model_def_fields(self):
        """From POV of document, indicates fields added/removed in model defs
        
        Adds the following fields:
        .model_def_fields_added
        .model_def_fields_removed
        .model_def_fields_added_msg
        .model_def_fields_removed_msg
        """
        model_def_fields(self)
    
    def form_prep(self):
        """Apply formprep_{field} functions to prep data dict to pass into DDRForm object.
        
        @returns data: dict object as used by Django Form object.
        """
        data = form_prep(self, self.identifier.fields_module())
        if not data.get('record_created', None):
            data['record_created'] = datetime.now()
        if not data.get('record_lastmod', None):
            data['record_lastmod'] = datetime.now()
        return data
    
    def form_post(self, form):
        """Apply formpost_{field} functions to process cleaned_data from DDRForm
        
        @param form: DDRForm object
        """
        form_post(self, self.identifier.fields_module(), form)
    
    def load_file_objects( self ):
        """Replaces list of file info dicts with list of DDRFile objects
        
        Overrides the function in .models.DDRLocalEntity, which
        adds DDRLocalFile objects which are missing certain methods of
        DDRFile.
        """
        self._file_objects = []
        for f in self.files:
            if f and f.get('path_rel',None):
                basename = os.path.basename(f['path_rel'])
                fid = os.path.splitext(basename)[0]
                identifier = Identifier(id=fid)
                file_ = DDRFile.from_identifier(identifier)
                self._file_objects.append(file_)
        # keep track of how many times this gets loaded...
        self._file_objects_loaded = self._file_objects_loaded + 1
    
    @staticmethod
    def create(collection, entity_id, git_name, git_mail, agent=settings.AGENT):
        """create new entity given an entity ID
        TODO remove write and commit, just create object
        """
        eidentifier = Identifier(id=entity_id)
        entity_path = eidentifier.path_abs()
        
        # write entity.json template to entity location and commit
        fileio.write_text(Entity(entity_path).dump_json(template=True),
                   settings.TEMPLATE_EJSON)
        exit,status = commands.entity_create(
            git_name, git_mail,
            collection, eidentifier,
            [collection.json_path_rel, collection.ead_path_rel],
            [settings.TEMPLATE_EJSON, settings.TEMPLATE_METS],
            agent=agent)
        
        # load new entity, inherit values from parent, write and commit
        entity = Entity.from_json(entity_path)
        entity.inherit(collection)
        entity.write_json()
        updated_files = [entity.json_path]
        exit,status = commands.entity_update(
            git_name, git_mail,
            collection, entity,
            updated_files,
            agent=agent)

        # delete cache, update search index
        collection.cache_delete()
        with open(entity.json_path, 'r') as f:
            document = json.loads(f.read())
        docstore.post(settings.DOCSTORE_HOSTS, settings.DOCSTORE_INDEX, document)
        
        return entity
    
    def save_part2( self, collection, updated_files, form_data, git_name, git_mail ):
        """Save entity part 2: the slow parts
        
        Commit files, delete cache, update search index.
        These steps are slow, should be called from tasks.entity_edit
        
        @param updated_files: list of paths
        @param collection: Collection
        @param git_name: str
        @param git_mail: str
        """
        inheritables = self.selected_inheritables(form_data)
        modified_ids,modified_files = self.update_inheritables(inheritables, form_data)
        if modified_files:
            updated_files = updated_files + modified_files
        
        exit,status = commands.entity_update(
            git_name, git_mail,
            collection, self,
            updated_files,
            agent=settings.AGENT)
        
        collection.cache_delete()
        with open(self.json_path, 'r') as f:
            document = json.loads(f.read())
        docstore.post(settings.DOCSTORE_HOSTS, settings.DOCSTORE_INDEX, document)
        return exit,status


class DDRFile( File ):
    
    @staticmethod
    def from_json(path_abs, identifier=None):
        """Instantiates a File object from specified *.json.
        
        @param path_abs: Absolute path to .json file.
        @returns: DDRFile
        """
        return from_json(DDRFile, path_abs, identifier)
    
    @staticmethod
    def from_identifier(identifier):
        """Instantiates a File object, loads data from FILE.json.
        
        @param identifier: Identifier
        @returns: File
        """
        return DDRFile.from_json(identifier.path_abs('json'), identifier)
    
    @staticmethod
    def from_request(request):
        """Instantiates a DDRFile object using django.http.HttpRequest.
        
        @param request: Request
        @returns: DDRFile
        """
        return DDRFile.from_identifier(Identifier(request))
    
    def collection(self):
        return Collection.from_identifier(self.identifier.collection())
    
    def parent(self):
        return Entity.from_identifier(self.identifier.parent())
    
    def absolute_url( self ):
        return reverse('webui-file', args=self.idparts)

    def delete_url(self): return reverse('webui-file-delete', args=self.idparts)
    def json_url(self): return reverse('webui-file-json', args=self.idparts)
    def edit_url(self): return reverse('webui-file-edit', args=self.idparts)
    def new_access_url(self): return reverse('webui-file-new-access', args=self.idparts)
    
    def access_url( self ):
        if self.access_rel:
            stub = os.path.join(self.entity_files_path.replace(settings.MEDIA_ROOT,''), self.access_rel)
            return '%s%s' % (settings.MEDIA_URL, stub)
        return None
    
    def fs_url( self ):
        """URL of the files directory browsable via Nginx.
        """
        return settings.MEDIA_URL + self.entity_files_path.replace(settings.MEDIA_ROOT, '')
    
    def gitweb_url( self ):
        """Returns local gitweb URL for files directory.
        """
        return '%s/?p=%s/.git;a=tree;f=%s;hb=HEAD' % (
            settings.GITWEB_URL,
            os.path.basename(self.collection_path),
            os.path.dirname(self.json_path_rel)
        )
    
    def media_url( self ):
        if self.path_rel:
            stub = os.path.join(self.entity_files_path.replace(settings.MEDIA_ROOT,''), self.path_rel)
            return '%s%s' % (settings.MEDIA_URL, stub)
        return None
    
    def model_def_commits(self):
        """Assesses document's relation to model defs in 'ddr' repo.
        
        Adds the following fields:
        .model_def_commits_alert
        .model_def_commits_msg
        """
        return model_def_commits(self)
    
    def model_def_fields(self):
        """From POV of document, indicates fields added/removed in model defs
        
        Adds the following fields:
        .model_def_fields_added
        .model_def_fields_removed
        .model_def_fields_added_msg
        .model_def_fields_removed_msg
        """
        model_def_fields(self)
    
    def form_prep(self):
        """Apply formprep_{field} functions to prep data dict to pass into DDRForm object.
        
        @returns data: dict object as used by Django Form object.
        """
        return form_prep(self, self.identifier.fields_module())
    
    def form_post(self, form):
        """Apply formpost_{field} functions to process cleaned_data from DDRForm
        
        @param form: DDRForm object
        """
        form_post(self, self.identifier.fields_module(), form)
    
    def save( self, git_name, git_mail ):
        """Perform file-save functions.
        
        Commit files, delete cache, update search index.
        These steps are to be called asynchronously from tasks.file_edit.
        
        @param collection: Collection
        @param file_id: str
        @param git_name: str
        @param git_mail: str
        """
        collection = self.collection()
        entity = self.parent()
        exit,status = commands.entity_update(
            git_name, git_mail,
            collection, entity,
            [self.json_path],
            agent=settings.AGENT)
        collection.cache_delete()
        with open(self.json_path, 'r') as f:
            document = json.loads(f.read())
        docstore.post(settings.DOCSTORE_HOSTS, settings.DOCSTORE_INDEX, document)
        return exit,status
