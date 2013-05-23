from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.decorators import available_attrs

from DDR import commands

from storage import REMOUNT_POST_REDIRECT_URL_SESSION_KEY



def storage_required(func):
    """Checks for storage; if problem redirects to remount page or shows error.
    
    Saves requested URI in session; remount view will try to retrieve and redirect.
    NOTE: We don't remember GET/POST args!!!
    """
    @wraps(func, assigned=available_attrs(func))
    def inner(request, *args, **kwargs):
        # if we can get list of collections, storage must be readable
        repo,org = settings.DDR_ORGANIZATIONS[0].split('-')
        try:
            collections = commands.collections_local(settings.DDR_BASE_PATH, repo, org)
            readable = True
        except:
            readable = False
        if not readable:
            status,msg = commands.storage_status(settings.DDR_BASE_PATH)
            remount_uri = request.META.get('PATH_INFO',None)
            request.session[REMOUNT_POST_REDIRECT_URL_SESSION_KEY] = remount_uri
            if msg == 'unmounted':
                messages.debug(request, '<b>{}</b>: {}'.format(REMOUNT_POST_REDIRECT_URL_SESSION_KEY, remount_uri))
                return HttpResponseRedirect(reverse('storage-remount0'))
            else:
                messages.error(request, 'ERROR: Could not get list of collections. Is USB HDD plugged in?')
            return HttpResponseRedirect(reverse('storage-required'))
        return func(request, *args, **kwargs)
    return inner
