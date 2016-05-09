from functools import wraps
import logging
logger = logging.getLogger(__name__)
import os

from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.decorators import available_attrs

from DDR import commands
from webui import models

from storage import STORAGE_MESSAGES
from storage import base_path
from webui import gitolite



def storage_required(func):
    """Checks for storage; if problem redirects to remount page or shows error.
    
    Our test for the presence of storage is whether or not the DDR subsystem
    can look for a list of collections in MEDIA_BASE.  It doesn't have to *find*
    any, but if the function completes it means the directory is readable.
    
    Note: Looks for list of collection repositories in MEDIA_BASE rather than
    storage.base_path, because the former is the path that is actually used by
    the higher-level parts of the app and by the www server.
    
    Saves requested URI in session; remount view will try to retrieve and redirect.
    NOTE: We don't remember GET/POST args!!!
    
    TODO This function will report unreadable if no collections for repo/org!
    """
    @wraps(func, assigned=available_attrs(func))
    def inner(request, *args, **kwargs):
        readable = False
        # if we can get list of collections, storage must be readable
        basepath = settings.MEDIA_BASE
        if not os.path.exists(basepath):
            msg = 'ERROR: Base path does not exist: %s' % basepath
            messages.error(request, msg)
            return HttpResponseRedirect(reverse('storage-required'))
        # realpath(MEDIA_BASE) indicates which Store is mounted
        basepathreal = os.path.realpath(settings.MEDIA_BASE)
        try:
            basepath_listdir = os.listdir(basepath)
        except OSError:
            basepath_listdir = []
        if not basepath_listdir:
            messages.error(request, 'ERROR: Base path exists but is not listable (probably the drive is not mounted).')
            return HttpResponseRedirect(reverse('storage-required'))
        repos_orgs = gitolite.get_repos_orgs()
        if repos_orgs:
            # propagate error
            if (type(repos_orgs) == type('')) and ('error' in repos_orgs):
                messages.error(request, repos_orgs)
                return HttpResponseRedirect(reverse('storage-required'))
            elif (type(repos_orgs) == type([])):
                repo,org = repos_orgs[0].split('-')
                try:
                    collections = models.Collection.collection_paths(settings.MEDIA_BASE, repo, org)
                    readable = True
                except:
                    messages.error(request, 'ERROR: Could not get collections list.')
        else:
            # If there are no repos/orgs, it may mean that the ddr user
            # is missing its SSH keys.
            messages.error(request, STORAGE_MESSAGES['NO_REPOS_ORGS'])
        if not readable:
            logger.debug('storage not readable')
            status,msg = commands.status(basepath)
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
