from collections import OrderedDict
import logging
logger = logging.getLogger(__name__)
import os

from elasticsearch.exceptions import ConnectionError

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.urlresolvers import reverse, NoReverseMatch

from rest_framework.reverse import reverse

from DDR import commands
from DDR import dvcs
from DDR import fileio
from DDR import modules
from DDR.models.common import from_json
from DDR.models.common import Stub as DDRStub
from DDR.models import Collection as DDRCollection
from DDR.models import Entity as DDREntity
from DDR.models import File as DDRFile

from webui import docstore
from webui import gitstatus
from webui import WEBUI_MESSAGES
from webui import COLLECTION_CHILDREN_CACHE_KEY
from webui import COLLECTION_FETCH_CACHE_KEY
from webui import COLLECTION_STATUS_CACHE_KEY
from webui import COLLECTION_ANNEX_STATUS_CACHE_KEY
from webui import COLLECTION_FETCH_TIMEOUT
from webui import COLLECTION_STATUS_TIMEOUT
from webui import COLLECTION_ANNEX_STATUS_TIMEOUT
from webui.identifier import Identifier, MODULES, VALID_COMPONENTS


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
            for model,module in MODULES.items()
        ]
        if not (valid_modules):
            valid = False
            messages.error(request, UNDEFINED_MSG)
    return valid

def model_def_commits(document):
    """
    Wrapper around DDR.models.model_def_commits
    
    @param document: Collection, Entity, File
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
    if added:
        document.model_def_fields_added = added
        document.model_def_fields_added_msg = WEBUI_MESSAGES['MODEL_DEF_FIELDS_ADDED'] % added
    if removed:
        document.model_def_fields_removed = removed
        document.model_def_fields_removed_msg = WEBUI_MESSAGES['MODEL_DEF_FIELDS_REMOVED'] % removed

def format_object(oi, d, request, is_detail=False):
    """Format detail or list objects for API
    
    Certain fields are always included (id, title, etc and links).
    Everything else is determined by what fields are in the result dict.
    
    d is basically an elasticsearch_dsl.Result, packaged by search.SearchResults.
    
    @param oi: Identifier
    @param d: dict
    @param request: 
    @param is_detail: boolean
    """
    try:
        collection_id = oi.collection_id()
    except:
        collection_id = None
    
    data = OrderedDict()
    data['id'] = d.pop('id')
    data['model'] = oi.model
    data['collection_id'] = collection_id
    data['links'] = make_links(oi, d, request, source='es', is_detail=is_detail)
    DETAIL_EXCLUDE = []
    for key,val in list(d.items()):
        if key not in DETAIL_EXCLUDE:
            data[key] = val
    return data

def make_links(oi, d, request, source='fs', is_detail=False):
    """Make the 'links pod' at the top of detail or list objects.
    
    @param oi: Identifier
    @param d: dict
    @param request: 
    @param source: str 'fs' (filesystem) or 'es' (elasticsearch)
    @param is_detail: boolean
    @returns: dict
    """
    assert source in ['fs', 'es']
    try:
        collection_id = oi.collection_id()
        child_models = oi.child_models(stubs=False)
    except:
        collection_id = None
        child_models = oi.child_models(stubs=True)
    
    img_url = ''
    if d.get('signature_id'):
        img_url = _access_url(Identifier(d['signature_id']))
    elif d.get('access_rel'):
        img_url = _access_url(oi)
    elif oi.model in ['repository','organization']:
        img_url = '%s%s/%s' % (
            settings.MEDIA_URL,
            oi.path_abs().replace(settings.MEDIA_ROOT, ''),
            'logo.png'
        )
    
    img_present = False
    if img_url:
        img_present = image_present(oi)
    
    links = OrderedDict()
    
    try:
        links['ui'] = reverse('webui-%s' % oi.model, args=([oi.id]), request=request)
    except NoReverseMatch:
        links['ui'] = ''
    
    links['api'] = reverse('api-%s-detail' % source, args=([oi.id]), request=request)
    
    # links to opposite
    if source == 'es':
        links['file'] = reverse('api-fs-detail', args=([oi.id]), request=request)
    elif source == 'fs':
        links['elastic'] = reverse('api-es-detail', args=([oi.id]), request=request)
    
    if is_detail:
        # objects above the collection level are stubs and do not have collection_id
        # collections have collection_id but have to point up to parent stub
        # API does not include stubs inside collections (roles)
        if collection_id and (collection_id != oi.id):
            parent_id = oi.parent_id(stubs=0)
        else:
            parent_id = oi.parent_id(stubs=1)
        if parent_id:
            links['parent'] = reverse('api-%s-detail' % source, args=[parent_id], request=request)
     
        if child_models:
            links['children'] = reverse('api-%s-children' % source, args=([oi.id]), request=request)
        else:
            links['children'] = ''

    links['img'] = img_url
    
    return links

def _access_url(fi):
    """
    @param oi: (optional) file Identifier
    """
    return '%s%s%s' % (
        settings.MEDIA_URL,
        fi.path_abs().replace(settings.MEDIA_ROOT, ''),
        settings.ACCESS_FILE_SUFFIX,
    )

def image_present(fi):
    return os.path.exists(
        '%s%s' % (fi.path_abs(), settings.ACCESS_FILE_SUFFIX)
    )

def docstore_url(oidentifier):
    """Returns local Elasticsearch URL for collection.
    
    >>> c = DDRLocalCollection('/tmp/ddr-testing-123')
    >>> c.docstore_url()
    'http://DOCSTORE_HOST/_docs/ddrcollection/ddr-testing-123/'
    """
    return 'http://{}/_doc/{}/{}'.format(
        settings.DOCSTORE_HOST, oidentifier.model, oidentifier.id
    )


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
    
    def children(self, quick=True):
        """Returns list of the Collection's Entity objects.
        """
        key = COLLECTION_CHILDREN_CACHE_KEY % self.id
        timeout = 60*15  # 1 hour
        cached = cache.get(key)
        if cached:
            return cached
        else:
            # note: these are AttrDicts
            kids = super(Collection, self).children(quick=quick)
            for o in kids:
                o.absolute_url = reverse('webui-entity', args=[o.id])
            cache.set(key, kids, timeout)
            return kids
    
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
        return reverse('webui-collection', args=[self.id])
    
    def admin_url(self): return reverse('webui-collection-admin', args=[self.id])
    def changelog_url(self): return reverse('webui-collection-changelog', args=[self.id])
    def check_url(self): return reverse('webui-collection-check', args=[self.id])
    def children_url(self): return reverse('webui-collection-children', args=[self.id])
    def edit_url(self): return reverse('webui-collection-edit', args=[self.id])
    def export_entities_url(self): return reverse('webui-collection-export-entities', args=[self.id])
    def export_files_url(self): return reverse('webui-collection-export-files', args=[self.id])
    def import_entities_url(self): return reverse('webui-collection-import-entities', args=[self.id])
    def import_files_url(self): return reverse('webui-collection-import-files', args=[self.id])
    def git_status_url(self): return reverse('webui-collection-git-status', args=[self.id])
    def merge_url(self): return reverse('webui-merge-raw', args=[self.id])
    def new_entity_url(self): return reverse('webui-entity-new', args=[self.id])
    def sync_url(self): return reverse('webui-collection-sync', args=[self.id])
    def signatures_url(self): return reverse('webui-collection-signatures', args=[self.id])
    
    def cgit_url( self ):
        """Returns cgit URL for collection.
        
        >>> c = DDRLocalCollection('/tmp/ddr-testing-123')
        >>> c.cgit_url()
        'http://partner.densho.org/cgit/cgit.cgi/ddr-testing-123/'
        """
        return '{}/cgit.cgi/{}/'.format(settings.CGIT_URL, self.id)
    
    def cgit_url_local( self ):
        """Returns local cgit URL for collection.
        
        >>> c = DDRLocalCollection('/tmp/ddr-testing-123')
        >>> c.cgit_url_local()
        '/cgit/cgit.cgi/ddr-testing-123/'
        """
        return '/cgit/cgit.cgi/{}/'.format(self.id)

    def api_url(self):
        """Returns local REST API URL for collection.
        
        >>> c = DDRLocalCollection('/tmp/ddr-testing-123')
        >>> c.api_url()
        '/ui/api/1.0/ddr-testing-123/'
        """
        return reverse('api-es-detail', args=([self.id]))
        
    def docstore_url( self ):
        """Returns local Elasticsearch URL for collection."""
        return docstore_url(self.identifier)
    
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
            return reverse('webui-collection-unlock', args=[self.id, unlock_task_id])
        return None
        
    def cache_delete( self ):
        cache.delete(COLLECTION_CHILDREN_CACHE_KEY % self.id)
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
        return reverse('webui-collection-sync-status-ajax', args=[self.id])
    
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
    
    @staticmethod
    def create(cidentifier, git_name, git_mail, agent=settings.AGENT):
        """Creates new Collection, writes files, performs initial commit
        """
        exit,status = commands.create(
            git_name, git_mail, cidentifier, agent
        )
        collection = Collection.from_identifier(cidentifier)
        
        # [delete cache], update search index
        #collection.cache_delete()
        if settings.DOCSTORE_ENABLED:
            try:
                docstore.Docstore().post(collection)
            except ConnectionError:
                logger.error('Could not post to Elasticsearch.')
        
        return exit,status
    
    def save( self, git_name, git_mail, cleaned_data={}, commit=True ):
        """Save Collection metadata.
        
        Commit files, delete cache, update search index.
        These steps are to be called asynchronously from tasks.collection_edit.
        
        @param git_name: str
        @param git_mail: str
        @param cleaned_data: dict
        """
        if cleaned_data:
            self.form_post(cleaned_data)
        
        exit,status,updated_files = super(Collection, self).save(
            git_name, git_mail,
            settings.AGENT,
            self.selected_inheritables(cleaned_data),
            commit=commit
        )
        
        self.cache_delete()
        if settings.DOCSTORE_ENABLED:
            try:
                docstore.Docstore().post(self)
            except ConnectionError:
                logger.error('Could not post to Elasticsearch.')
        
        return exit,status,updated_files


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
        return reverse('webui-entity', args=[self.id])
    
    def addfilelog_url(self): return reverse('webui-entity-addfilelog', args=[self.id])
    def changelog_url(self): return reverse('webui-entity-changelog', args=[self.id])
    def delete_url(self): return reverse('webui-entity-delete', args=[self.id])
    def edit_url(self): return reverse('webui-entity-edit', args=[self.id])
    
    def new_file_url(self, role):
        return reverse('webui-file-new', args=[ '-'.join([self.id, role]) ])
    
    def children_url(self, role):
        return reverse('webui-file-role', args=[ '-'.join([self.id, role]) ])
    
    def file_batch_url(self, role):
        args = [a for a in self.idparts]
        args.append(role)
        return reverse('webui-file-batch', args=args)
    
    def file_browse_url(self, role):
        idparts = self.identifier.idparts
        idparts['model'] = 'file-role'
        idparts['role'] = role
        ri = Identifier(idparts)
        return reverse('webui-file-browse', args=[ri.id])
    
    def file_external_url(self, role):
        idparts = self.identifier.idparts
        idparts['model'] = 'file-role'
        idparts['role'] = role
        ri = Identifier(idparts)
        return reverse('webui-file-new-external', args=[ri.id])
    
    def children_urls(self, active=None):
        """Generate data for populating entity children/roles tabs
        """
        tabs = [
            {
                'name': role,
                'url': self.children_url(role),
                'active': role == active,
                'count': count,
            }
            for role,count in self.children_counts().items()
        ]
        tabs[0]['url'] = reverse('webui-entity-children', args=[self.id])
        return tabs
    
    def file_batch_urls(self, active=None):
        return [
            {'url': self.file_batch_url(role), 'name': role, 'active': role == active}
            for role in VALID_COMPONENTS['role']
        ]
    
    def file_browse_urls(self, active=None):
        return [
            {'url': self.file_browse_url(role), 'name': role, 'active': role == active}
            for role in VALID_COMPONENTS['role']
        ]
    
    def fs_url( self ):
        """URL of the entity directory browsable via Nginx.
        """
        return settings.MEDIA_URL + os.path.dirname(self.json_path).replace(settings.MEDIA_ROOT, '')
    
    def cgit_url( self ):
        """Returns cgit URL for entity.
        
        >>> e = DDRLocalEntity('/tmp/ddr-testing-123-456')
        >>> e.cgit_url()
        'http://partner.densho.org/cgit/cgit.cgi/ddr-testing-123/tree/files/ddr-testing-123/'
        """
        return '{}/cgit.cgi/{}/tree/files/{}'.format(
            settings.CGIT_URL,
            self.collection_id,
            self.id
        )
    
    def cgit_url_local( self ):
        """Returns local cgit URL for entity.
        
        >>> e = DDRLocalEntity('/tmp/ddr-testing-123-456')
        >>> e.cgit_url()
        '/cgit/cgit.cgi/ddr-testing-123/tree/files/ddr-testing-123/'
        """
        return '/cgit/cgit.cgi/{}/tree/files/{}'.format(
            self.collection_id,
            self.id
        )

    def api_url(self):
        """Returns local REST API URL for entity.
        
        >>> e = DDRLocalEntity('/tmp/ddr-testing-123-456')
        >>> e.api_url()
        '/ui/api/1.0/ddr-testing-123-456/'
        """
        return reverse('api-es-detail', args=([self.id]))
    
    def docstore_url( self ):
        """Returns local Elasticsearch URL for collection."""
        return docstore_url(self.identifier)
    
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
            return reverse('webui-entity-unlock', args=[self.id, unlock_task_id])
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
    
    def load_file_objects(self, identifier_class, object_class, force_read=False):
        """Replaces list of file info dicts with list of File objects
        
        Overrides the function in .models.DDRLocalEntity, which
        adds DDRLocalFile objects which are missing certain methods of
        File.
        """
        super(Entity, self).load_file_objects(
            Identifier,
            File,
            force_read=force_read
        )
    
    @staticmethod
    def create(eidentifier, git_name, git_mail, agent=settings.AGENT):
        """Creates new Entity, writes files, performs initial commit
        """
        collection = eidentifier.collection().object()
        exit,status = commands.entity_create(
            user_name=git_name,
            user_mail=git_mail,
            collection=collection,
            eidentifier=eidentifier,
            updated_files=[],
            agent=agent,
        )
        # load new entity, inherit values from parent, write and commit
        entity = eidentifier.object()
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
        if settings.DOCSTORE_ENABLED:
            try:
                docstore.Docstore().post(entity)
            except ConnectionError:
                logger.error('Could not post to Elasticsearch.')
        
        return exit,status
    
    def save( self, git_name, git_mail, agent=settings.AGENT, collection=None, cleaned_data={}, commit=True ):
        """Save Entity metadata
        
        Commit files, delete cache, update search index.
        These steps are slow, should be called from tasks.entity_edit
        
        @param git_name: str
        @param git_mail: str
        @param collection: Collection
        @param cleaned_data: dict
        """
        collection = self.collection()
        if cleaned_data:
            self.form_post(cleaned_data)
        
        exit,status,updated_files = super(Entity, self).save(
            git_name=git_name,
            git_mail=git_mail,
            agent=settings.AGENT,
            collection=collection,
            inheritables=self.selected_inheritables(cleaned_data),
            commit=commit
        )
        
        collection.cache_delete()
        if settings.DOCSTORE_ENABLED:
            try:
                docstore.Docstore().post(self)
            except ConnectionError:
                logger.error('Could not post to Elasticsearch.')
        
        return exit,status,updated_files


class File( DDRFile ):
    
    @staticmethod
    def from_json(path_abs, identifier=None, inherit=True):
        """Instantiates a File object from specified *.json.
        
        @param path_abs: Absolute path to .json file.
        @param inherit: boolean Whether to inherit values from ancestor(s)
        @returns: File
        """
        return from_json(File, path_abs, identifier, inherit=inherit)
    
    @staticmethod
    def from_identifier(identifier, inherit=True):
        """Instantiates a File object, loads data from FILE.json.
        
        @param identifier: Identifier
        @param inherit: boolean Whether to inherit values from ancestor(s)
        @returns: File
        """
        return File.from_json(identifier.path_abs('json'), identifier, inherit=inherit)
    
    @staticmethod
    def from_request(request):
        """Instantiates a File object using django.http.HttpRequest.
        
        @param request: Request
        @returns: File
        """
        return File.from_identifier(Identifier(request))
    
    def collection(self):
        return Collection.from_identifier(self.identifier.collection())
    
    def parent(self):
        return Entity.from_identifier(self.identifier.parent())
    
    def absolute_url( self ):
        return reverse('webui-file', args=[self.id])

    def delete_url(self): return reverse('webui-file-delete', args=[self.id])
    def edit_url(self): return reverse('webui-file-edit', args=[self.id])
    def new_access_url(self): return reverse('webui-file-new-access', args=[self.id])
    
    def access_url( self ):
        if self.access_rel:
            mediaroot = os.path.join(settings.MEDIA_ROOT, '') # append trailing slash
            path_rel = os.path.normpath(self.access_abs.replace(mediaroot, ''))
            return os.path.join(settings.MEDIA_URL, path_rel)
        return None

    def media_path( self ):
        return os.path.dirname(self.path_abs)
    
    def media_url( self ):
        if self.path_rel:
            mediaroot = os.path.join(settings.MEDIA_ROOT, '') # append trailing slash
            path_rel = os.path.normpath(self.path_abs.replace(mediaroot, ''))
            return os.path.join(settings.MEDIA_URL, path_rel)
        return None

    def api_url(self):
        """Returns local REST API URL for file.
        
        >>> f = File('/tmp/ddr-testing-123-456-master-abc123')
        >>> f.api_url()
        '/ui/api/1.0/ddr-testing-123-456-master-abc123/'
        """
        return reverse('api-es-detail', args=([self.id]))
    
    def docstore_url( self ):
        """Returns local Elasticsearch URL for collection."""
        return docstore_url(self.identifier)
    
    def fs_url( self ):
        """URL of the files directory browsable via Nginx.
        """
        return os.path.dirname(self.media_url())
    
    def gitweb_url( self ):
        """Returns local gitweb URL for files directory.
        """
        return '%s/?p=%s/.git;a=tree;f=%s;hb=HEAD' % (
            settings.GITWEB_URL,
            os.path.basename(self.collection_path),
            os.path.dirname(self.json_path_rel)
        )
    
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
    
    def save( self, git_name, git_mail, agent=settings.AGENT, cleaned_data={}, commit=True ):
        """Save file metadata
        
        Commit files, delete cache, update search index.
        These steps are to be called asynchronously from tasks.file_edit.
        
        @param git_name: str
        @param git_mail: str
        @param cleaned_data: dict
        """
        collection = self.collection()
        if cleaned_data:
            self.form_post(cleaned_data)
        
        exit,status,updated_files = super(File, self).save(
            git_name=git_name,
            git_mail=git_mail,
            agent=settings.AGENT,
            collection=collection,
            parent=self.parent(),
            inheritables=self.selected_inheritables(cleaned_data),
            commit=commit
        )
        
        collection.cache_delete()
        if settings.DOCSTORE_ENABLED:
            try:
                docstore.Docstore().post(self)
            except ConnectionError:
                logger.error('Could not post to Elasticsearch.')
        
        return exit,status,updated_files
