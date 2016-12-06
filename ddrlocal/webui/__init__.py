import logging
logger = logging.getLogger(__name__)

from django.conf import settings

from DDR.docstore import make_index_name, index_exists, target_index


COLLECTION_FETCH_CACHE_KEY = 'webui:collection:%s:fetch'
COLLECTION_STATUS_CACHE_KEY = 'webui:collection:%s:status'
COLLECTION_ANNEX_STATUS_CACHE_KEY = 'webui:collection:%s:annex_status'
GITOLITE_INFO_CACHE_KEY = 'ddrlocal:gitolite_info'

COLLECTION_FETCH_TIMEOUT = 0
COLLECTION_STATUS_TIMEOUT = 60 * 10
COLLECTION_ANNEX_STATUS_TIMEOUT = 60 * 10


WEBUI_MESSAGES = {
    
    # webui.api
    'API_LOGIN_NOT_200': 'Error: status code {} on POST', # status code
    'API_LOGIN_INVALID_EMAIL': 'Your email is invalid! Please log in to workbench and enter a valid email!',
    'API_LOGIN_INVALID_NAME': 'Please log in to workbench and enter your first/last name(s).',
    
    # webui.views
    'ERROR': 'Error: {}', # error code
    'LOGIN_REQUIRED': 'Login is required',
    'LOGIN_SUCCESS': 'Logged in as <strong>{}</strong>.', # username
    'LOGIN_FAIL': "Couldn't log in. Please enter a valid username and password.", # status code
    'LOGOUT_SUCCESS': 'Logged out <strong>{}</strong>.', # username
    'LOGOUT_FAIL': "Couldn't log out ({}).", # status code
    
    # webui.views.collections
    'VIEWS_COLL_SYNCED': 'Collection synced with server: {}', # collection id
    'VIEWS_COLL_CREATED': 'New collection created: {}',
    'VIEWS_COLL_ERR_NO_IDS': 'Error: Could not get new collection ID from ID service (%s): %s',
    'VIEWS_COLL_ERR_CREATE': 'Error: Could not create new collection.',
    'VIEWS_COLL_UPDATED': 'Collection updated',
    'VIEWS_COLL_LOCKED': 'Collection is locked: <strong>{}</strong>', # collection_id
    'VIEWS_COLL_BEHIND': 'Collection <strong>{}</strong> is behind and needs to be synced.', # collection_id
    'VIEWS_COLL_CONFLICTED': 'Collection <strong>{}</strong> is in a conflicted state. <a href="{}">Click here to resolve.</a>', # collection_id, url
    
    # webui.views.entities
    'VIEWS_ENT_CREATED': 'New object created: {}', # entity id
    'VIEWS_ENT_ERR_NO_IDS': 'Error: Could not get new object ID from ID service (%s): %s',
    'VIEWS_ENT_ERR_CREATE': 'Error: Could not create new object.',
    'VIEWS_ENT_UPDATED': 'Object updated',
    'VIEWS_ENT_LOCKED': 'This object is locked.',
    
    # webui.views.files
    'VIEWS_FILES_UPLOADING': 'Uploading <b>%s</b> (%s)', # filename, original filename
    'VIEWS_FILES_PARENT_LOCKED': "This file's parent object is locked.",
    'VIEWS_FILES_UPDATED': 'File metadata updated',
    'VIEWS_FILES_NEWACCESS': 'Generating access file for <strong>%s</strong>.', # filename
    
    # webui.models.model_def_commits
    'MODEL_DEF_COMMITS_STATUS_-m': ('warning', "Missing model definitions commit info."),
    'MODEL_DEF_COMMITS_STATUS_-d': ('warning', "Missing document commit info."),
    # 'a!' and 'b!' occur if source code was on an unmerged branch when document was committed
    'MODEL_DEF_COMMITS_STATUS_a!': ('warning', "Model definitions commit A not in commit log."),
    'MODEL_DEF_COMMITS_STATUS_b!': ('warning', "Model definitions commit B not in commit log."),
    'MODEL_DEF_COMMITS_STATUS_lt': ('info', "Document model definitions OLDER than module's."),
    'MODEL_DEF_COMMITS_STATUS_eq': ('info', "Document model definitions SAME as module's."),
    'MODEL_DEF_COMMITS_STATUS_gt': ('info', "Document model definitions NEWER than module's."),
    
    # webui.models.model_def_fields
    'MODEL_DEF_FIELDS_ADDED': "The following fields will be added to this docment the next time you edit. {}",
    'MODEL_DEF_FIELDS_REMOVED': "The following fields in this document are absent from the repository's model definitions. If you edit this document these fields and their data will disappear! {}",

}

def set_docstore_index( request ):
    """Ensure active Elasticsearch index matches active storage; complain if not.
    
    Look at mounted storage. Make an index name based on that.
    If mounted and corresponding index exists in Elasticsearch, make sure it's
    in session.  If index is in session but storage not mounted or Elasticearch
    index doesn't exist, remove from session.
    
    storage_label: label of storage currently in session
    docstore_index_exists: Elasticsearch index exists for storage_label (or not)
    
    @param request:
    @returns: storage_label,docstore_index_exists
    """
    # gather info
    docstore_index = None
    docstore_index_exists = None
    storage_label = request.session.get('storage_label', None)
    if not storage_label:
        storage_label = target_index(settings.DOCSTORE_HOSTS, settings.DOCSTORE_INDEX)
    if storage_label:
        docstore_index = make_index_name(storage_label)
        if docstore_index:
            docstore_index_exists = index_exists(settings.DOCSTORE_HOSTS, docstore_index)
    # rm index from session
    if not (storage_label or docstore_index_exists):
        request.session['docstore_index'] = None
    # add index to session
    if storage_label and docstore_index_exists and not request.session.get('docstore_index',None):
        request.session['docstore_index'] = docstore_index
    return storage_label,docstore_index_exists
