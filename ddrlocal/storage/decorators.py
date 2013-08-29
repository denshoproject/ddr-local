from functools import wraps
import logging
logger = logging.getLogger(__name__)

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.decorators import available_attrs

from DDR import commands

from storage import STORAGE_MESSAGES
from storage import base_path



def get_repos_orgs():
    """Returns list of repo-orgs that the current SSH key gives access to.
    
    Hits up Gitolite for the info.
    """
    key = 'ddrlocal:gitolite_repos_orgs'
    repos_orgs = cache.get(key)
    if not repos_orgs:
        repos_orgs = []
        status,lines = commands.gitolite_info()
        for line in lines:
            if 'R W C' in line:
                parts = line.replace('R W C', '').strip().split('-')
                repo_org = '-'.join([parts[0], parts[1]])
                if repo_org not in repos_orgs:
                    repos_orgs.append(repo_org)
        cache.set(key, repos_orgs, settings.REPOS_ORGS_TIMEOUT)
    return repos_orgs

def storage_required(func):
    """Checks for storage; if problem redirects to remount page or shows error.
    
    Looks for list of collection repositories in MEDIA_BASE rather than
    storage.base_path, because the former is the path that is actually used by
    the higher-level parts of the app and by the www server.
    
    Saves requested URI in session; remount view will try to retrieve and redirect.
    NOTE: We don't remember GET/POST args!!!
    """
    @wraps(func, assigned=available_attrs(func))
    def inner(request, *args, **kwargs):
        # if we can get list of collections, storage must be readable
        basepath = settings.MEDIA_BASE
        repos_orgs = get_repos_orgs()
        repo,org = repos_orgs[0].split('-')
        try:
            collections = commands.collections_local(basepath, repo, org)
            readable = True
        except:
            readable = False
        if not readable:
            logger.debug('storage not readable')
            status,msg = commands.storage_status(basepath)
            logger.debug('storage status: %s' % status)
            logger.debug('storage msg: %s' % msg)
            remount_uri = request.META.get('PATH_INFO',None)
            request.session[settings.REDIRECT_URL_SESSION_KEY] = remount_uri
            if msg == 'unmounted':
                messages.debug(request, '<b>{}</b>: {}'.format(settings.REDIRECT_URL_SESSION_KEY, remount_uri))
                return HttpResponseRedirect(reverse('storage-remount0'))
            else:
                messages.error(request, STORAGE_MESSAGES['ERROR'])
            return HttpResponseRedirect(reverse('storage-required'))
        return func(request, *args, **kwargs)
    return inner
