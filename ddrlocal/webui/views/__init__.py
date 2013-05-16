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
            s = api.login(request,
                          form.cleaned_data['username'],
                          form.cleaned_data['password'])
            if s and (type(s) != type('')) and s.cookies.get('sessionid', None):
                messages.success(
                    request,
                    'Logged in as <strong>{}</strong>.'.format(form.cleaned_data['username']))
                return HttpResponseRedirect( reverse('webui-index') )
            else:
                messages.warning(
                    request,
                    "Couldn't log in. Please enter a valid username and password.")
    else:
        form = LoginForm()
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
        messages.success(request, 'Logged out')
    else:
        messages.warning(request, "Couldn't log out ({}).".format(status))
    return HttpResponseRedirect( reverse('webui-index') )
