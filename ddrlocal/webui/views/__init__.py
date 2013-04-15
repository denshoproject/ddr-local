import logging
logger = logging.getLogger(__name__)
import os

from bs4 import BeautifulSoup
import requests

from django.conf import settings
from django.contrib import messages
from django.core.context_processors import csrf
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import Http404, get_object_or_404, render_to_response
from django.template import RequestContext

from Kura import commands

from webui.forms import LoginForm

# helpers --------------------------------------------------------------

def do_logout():
    """Logs out of the workbench server.
    @returns string: 'ok' or error message
    """
    r = requests.get(settings.WORKBENCH_LOGOUT_URL)
    if r.status_code == 200:
        return 'ok'
    return 'error: unspecified'

def do_login(username, password):
    """Logs in to the workbench server.
    @returns string: sessionid or error message (starting with 'error:')
    """
    if not (username or password):
        return 'error: missing username or password'
    # load test page to see if already logged in
    r = requests.get(settings.WORKBENCH_LOGIN_TEST)
    soup = BeautifulSoup(r.text)
    titletag = soup.find('title')
    if (r.status_code == 200) and not ('Log in' in titletag.string):
        return r.cookies.get('sessionid')
    # get CSRF token from cookie
    csrf_token = r.cookies['csrftoken']
    # log in
    headers = {'X-CSRFToken': csrf_token}
    cookies = {'csrftoken': csrf_token}
    data = {'csrftoken': csrf_token,
            'username': username,
            'password': password,}
    r1 = requests.post(settings.WORKBENCH_LOGIN_URL,
                       headers=headers,
                       cookies=cookies,
                       data=data,)
    if r1.status_code != 200:
        return 'error: status code {} on POST'.format(r1.status_code)
    # it would be better to look for a success message...
    error_msg = 'Please enter a correct username and password.'
    if r1.text:
        if (error_msg not in r1.text):
            return r1.cookies.get('sessionid')
        else:
            return 'error: bad username or password'
    return 'error: unspecified'


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
            sessionid = do_login(form.cleaned_data['username'],
                                 form.cleaned_data['password'])
            if 'error' not in sessionid:
                request.session['workbench_sessionid'] = sessionid
                request.session['username'] = form.cleaned_data['username']
                request.session['git_name'] = form.cleaned_data['git_name'] 
                request.session['git_mail'] = form.cleaned_data['git_mail'] 
                messages.success(
                    request,
                    'Logged in as <strong>{}</strong>.'.format(form.cleaned_data['username']))
            else:
                messages.warning(
                    request,
                    "Couldn't log in ({}).".format(sessionid))
            return HttpResponseRedirect( reverse('webui-index') )
    else:
        form = LoginForm()
    return render_to_response(
        'webui/login.html',
        {'form': form,},
        context_instance=RequestContext(request, processors=[])
    )

def logout( request ):
    status = do_logout()
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
