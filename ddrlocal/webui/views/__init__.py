import logging
logger = logging.getLogger(__name__)

from django.conf import settings
from django.contrib import messages
from django.core.context_processors import csrf
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import Http404, get_object_or_404, render_to_response
from django.template import RequestContext

from DDR import commands

from webui import WEBUI_MESSAGES
from webui import api
from webui.forms import LoginForm

# helpers --------------------------------------------------------------


# views ----------------------------------------------------------------

"""
local takes username/passwd
in background makes request to mits using that username/password
gets the response
figures out if successful/not
if successful:
    stores in memcached session

what do we need to store?
- username
- user name  (for git logs)
- user email (for git logs)
- repo
- orgs the user belongs to
"""

def login( request ):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            redirect_uri = form.cleaned_data['next']
            if not redirect_uri:
                redirect_uri = reverse('webui-index')
            s = api.login(request,
                          form.cleaned_data['username'],
                          form.cleaned_data['password'])
            if s and (type(s) != type('')) and s.cookies.get('sessionid', None):
                messages.success(
                    request,
                    WEBUI_MESSAGES['LOGIN_SUCCESS'].format(form.cleaned_data['username']))
                return HttpResponseRedirect(redirect_uri)
            else:
                messages.warning(request, WEBUI_MESSAGES['LOGIN_FAIL'])
    else:
        form = LoginForm(initial={'next':request.GET.get('next',''),})
        # Using "initial" rather than passing in data dict lets form include
        # redirect link without complaining about blank username/password fields.
    return render_to_response(
        'webui/login.html',
        {'form': form,},
        context_instance=RequestContext(request, processors=[])
    )

def logout( request ):
    status = api.logout()
    if status == 'ok':
        # remove user info from session
        request.session['workbench_sessionid'] = None
        request.session['username'] = None
        request.session['git_name'] = None
        request.session['git_mail'] = None
        # feedback
        messages.success(request, WEBUI_MESSAGES['LOGOUT_SUCCESS'])
    else:
        messages.warning(request, WEBUI_MESSAGES['LOGOUT_FAIL'].format(status))
    return HttpResponseRedirect( reverse('webui-index') )
