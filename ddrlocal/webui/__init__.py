import logging
logger = logging.getLogger(__name__)

from django.conf import settings
from django.core.cache import cache

from DDR import commands
from DDR.docstore import make_index_name, index_exists
from DDR.dvcs import gitolite_info, gitolite_orgs
from storage import base_path


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
    'VIEWS_COLL_ERR_NO_IDS': 'Error: Could not get new collection IDs from workbench.',
    'VIEWS_COLL_ERR_CREATE': 'Error: Could not create new collection.',
    'VIEWS_COLL_UPDATED': 'Collection updated',
    'VIEWS_COLL_LOCKED': 'Collection is locked: <strong>{}</strong>', # collection_id
    'VIEWS_COLL_BEHIND': 'Collection <strong>{}</strong> is behind and needs to be synced.', # collection_id
    'VIEWS_COLL_CONFLICTED': 'Collection <strong>{}</strong> is in a conflicted state. <a href="{}">Click here to resolve.</a>', # collection_id, url
    
    # webui.views.entities
    'VIEWS_ENT_CREATED': 'New object created: {}', # entity id
    'VIEWS_ENT_ERR_NO_IDS': 'Error: Could not get new object IDs from workbench.',
    'VIEWS_ENT_ERR_CREATE': 'Error: Could not create new object.',
    'VIEWS_ENT_UPDATED': 'Object updated',
    'VIEWS_ENT_LOCKED': 'This object is locked.',
    
    # webui.views.files
    'VIEWS_FILES_UPLOADING': 'Uploading <b>%s</b> (%s)', # filename, original filename
    'VIEWS_FILES_PARENT_LOCKED': "This file's parent object is locked.",
    'VIEWS_FILES_UPDATED': 'File metadata updated',
    'VIEWS_FILES_NEWACCESS': 'Generating access file for <strong>%s</strong>.' # filename
    
}


def get_repos_orgs():
    """Returns list of repo-orgs that the current SSH key gives access to.
    
    Hits up Gitolite for the info.
    
    If no repos/orgs are returned it probably means that the ddr user's
    SSH keys are missing or invalid.  The repos_orgs value is still cached
    for 1 minute to prevent flapping.
    """
    key = 'ddrlocal:gitolite_repos_orgs'
    repos_orgs = cache.get(key)
    if not repos_orgs:
        status,lines = gitolite_info(settings.GITOLITE)
        if status and not lines:
            logging.error('commands.gitolite_info() status:%s, lines:%s' % (status,lines))
            logging.error('| Is ddr missing its SSH keys?')
        repos_orgs = gitolite_orgs(lines)
        if repos_orgs:
            cache.set(key, repos_orgs, settings.REPOS_ORGS_TIMEOUT)
        else:
            cache.set(key, repos_orgs, 60*1) # 1 minute
    return repos_orgs

def set_docstore_index( request ):
    """Ensure active Elasticsearch index matches active storage; complain if not.
    
    Look at mounted storage. Make an index name based on that.
    If mounted and corresponding index exists in Elasticsearch, make sure it's
    in session.  If index is in session but storage not mounted or Elasticearch
    index doesn't exist, remove from session.
    """
    # gather info
    docstore_index = None
    docstore_index_exists = None
    storage_label = request.session.get('storage_label', None)
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
