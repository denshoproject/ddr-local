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

from DDR import commands

from webui import api
from webui.forms import LoginForm, MountForm, UmountForm

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
                request.session['git_name'] = form.cleaned_data['git_name'] 
                request.session['git_mail'] = form.cleaned_data['git_mail'] 
                messages.success(
                    request,
                    'Logged in as <strong>{}</strong>.'.format(form.cleaned_data['username']))
            else:
                messages.warning(
                    request,
                    "Couldn't log in ({}).".format(session))
            return HttpResponseRedirect( reverse('webui-index') )
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

def storage( request ):
    """
    TODO THIS IS HORRIBLY INSECURE YOU ID10T!!!  >:^O
    """
    stat,removables = commands.removables()
    stat,mounted = commands.removables_mounted()
    if request.method == 'POST':
        mount_form = MountForm(request.POST)
        umount_form = UmountForm(request.POST)
        which = request.POST.get('which','neither')
        if which == 'mount':
            if mount_form.is_valid():
                devicefile,label,mounted = None,None,None
                value = request.POST.get('submit',None)
                if value:
                    op,devicefile,label = value.split(' ')
                if devicefile and label:
                    stat,mounted = commands.mount(devicefile, label)
                if mounted:
                    messages.success(request, 'Mounted {}'.format(label))
                elif mounted == False:
                    messages.warning(request, 'Count not mount {}'.format(label))
                else:
                    messages.error(request, 'Problem mounting {}: {},{}'.format(label, stat,mounted))
                return HttpResponseRedirect( reverse('webui-storage') )
        elif which == 'umount':
            if umount_form.is_valid():
                mountpoint,devicefile,unmounted = None,None,None
                value = request.POST.get('submit',None)
                if value:
                    mountpoint = value.split(' ')[1]
                if mountpoint:
                    for m in mounted:
                        mountpath = m.get('mountpath',None)
                        if mountpath and (mountpath == mountpoint):
                            devicefile = m['devicefile']
                if devicefile:
                    stat,unmounted = commands.umount(devicefile)
                if unmounted:
                    messages.success(request, 'Umounted {}'.format(value))
                elif unmounted == False:
                    messages.warning(request, 'Count not umount {}'.format(value))
                else:
                    messages.error(request, 'Problem unmounting {}: {},{}'.format(value, stat,unmounted))
                return HttpResponseRedirect( reverse('webui-storage') )
    else:
        mount_form = MountForm()
        umount_form = UmountForm()
    return render_to_response(
        'webui/storage.html',
        {'removables': removables,
         'removables_mounted': mounted,
         'mount_form': mount_form,
         'umount_form': umount_form,
        },
        context_instance=RequestContext(request, processors=[])
    )

def storage_required( request ):
    return render_to_response(
        'webui/storage-required.html',
        {},
        context_instance=RequestContext(request, processors=[])
    )
