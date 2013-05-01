from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.decorators import available_attrs

from DDR import commands

def login_required(func):
    """Checks for git_name,git_main in session; redirects to login if absent
    """
    @wraps(func, assigned=available_attrs(func))
    def inner(request, *args, **kwargs):
        git_name = request.session.get('git_name')
        git_mail = request.session.get('git_mail')
        if not (git_name and git_mail):
            url = reverse('webui-login')
            #url = '%s?next=%s'.format(reverse('webui-login'), request.META['PATH_INFO'])
            return HttpResponseRedirect(url)
        return func(request, *args, **kwargs)
    return inner

def storage_required(func):
    """Checks for presence of storage; redirects to mount page if absent
    """
    def storage_present():
        try:
            repo,org = settings.DDR_ORGANIZATIONS[0].split('-')
            collections = commands.collections_local(settings.DDR_BASE_PATH, repo, org)
            return True
        except:
            pass
        return False
    
    @wraps(func, assigned=available_attrs(func))
    def inner(request, *args, **kwargs):
        if not storage_present():
            messages.error(request, 'ERROR: Could not get list of collections. Is USB HDD plugged in?')
            return HttpResponseRedirect(reverse('webui-storage-required'))
        return func(request, *args, **kwargs)
    return inner
