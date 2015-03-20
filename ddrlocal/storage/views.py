import logging
logger = logging.getLogger(__name__)
import os

from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import Http404, get_object_or_404, render_to_response, redirect
from django.template import RequestContext

from DDR import commands
from DDR import docstore

from webui.tasks import reindex_and_notify
import storage
from storage.forms import StorageForm
from storage.tasks import mount_in_bkgnd


# helpers --------------------------------------------------------------

def get_unmounted(removablez):
    unmounted = []
    for r in removablez:
        ismounted = int(r.get('ismounted', '-1'))
        if not (ismounted == 1):
            unmounted.append(r)
    return unmounted

def unmounted_devices():
    return [(d['devicefile'],d['label']) for d in get_unmounted(removables())]

def mounted_devices():
    return [(d['mountpath'],d['devicefile']) for d in storage.removables_mounted()]

def add_manual_symlink(devices):
    """Adds manually-set symlink to list of mounted devices if present.
    See storage.views.manual_symlink.
    """
    path = storage.media_base_target()
    for r in devices:
        if path and (r[0] in path):
            path = None
    if path:
        devices.append( (path,'') )
    return devices



# views ----------------------------------------------------------------

def index( request ):
    """Interface for mounting/unmounting drives and setting active device
    """
    devices = storage.removables()
    # put form data for each action button in devices
    for device in devices:
        device['action_forms'] = []
        for action in device['actions']:
            form = {
                'url': reverse(
                    'storage-operation', args=(action, device['devicetype'],)),
                'action': action,
            }
            device['action_forms'].append(form)
    return render_to_response(
        'storage/index.html',
        {
            'removables': devices,
        },
        context_instance=RequestContext(request, processors=[])
    )

def operation( request, opcode, devicetype ):
    """Mount/unmount or link/unlink a device.
    """
    if opcode not in ['mount', 'unmount', 'link', 'unlink']:
        raise Http404
    if request.method == 'POST':
        form = StorageForm(request.POST)
        if form.is_valid():
            devicefile = form.cleaned_data['device']
            
            if opcode == 'mount':
                mount_in_bkgnd.apply_async((devicetype, devicefile,), countdown=2)
                status,msg = 0,'mounting'
                messages.success(request, 'Mounting device. Please be patient.')
            elif opcode == 'unmount':
                status,msg = storage.unmount(request, devicetype, devicefile)
            elif opcode == 'link':
                status,msg = storage.link(request, devicetype, devicefile)
            elif opcode == 'unlink':
                status,msg = storage.unlink(request, devicetype, devicefile)
            
            #if status == 'ok':
            #    messages.success(request, msg)
            #else:
            #    messages.warning(request, msg)
    
    return HttpResponseRedirect( reverse('storage-index') )

def remount0( request ):
    """Show a spinning beachball while we try to remount the storage.
    This is just a static page that gives the user something to look at
    while remount1 is running.
    """
    remount_uri = request.session.get(
        settings.REDIRECT_URL_SESSION_KEY,
        reverse('storage-index'))
    return render_to_response(
        'storage/remount.html',
        {'remount_uri':remount_uri,},
        context_instance=RequestContext(request, processors=[])
    )

def remount1( request ):
    """
    NOTES:
    Storage device's device file, label, and mount_path are stored in session
    on mount and removed from session on unmount.
    When the VM is suspended and resumed, the device often becomes available
    with a different device file (i.e. /dev/sdc1 instead of /dev/sdb1).
    The device is still "mounted" with the old device file.
    We need to unmount from the old device file and remount with the new
    device file that we get from looking directly at the system's device info.
    """
    remount_uri = request.session.get(settings.REDIRECT_URL_SESSION_KEY, None)
    # device label
    label = request.session.get('storage_label', None)
    # current "mounted" devicefile
    devicefile_session = request.session.get('storage_devicefile', None)
    # the actual new devicefile
    devicefile_udisks = None
    if label:
        for d in removables():
            if d['label'] == label:
                devicefile_udisks = d['devicefile']
    # unmount, mount
    unmounted,mount_path = None,None
    remount_attempted = False
    if devicefile_session and label and devicefile_udisks:
        unmounted = unmount(request, devicefile_session, label)
        mount_path = mount(request, devicefile_udisks, label)
        remount_attempted = True
    else:
        messages.warning(request, storage.STORAGE_MESSAGES['REMOUNT_FAIL'])
    # redirect
    url = reverse('storage-index')
    if remount_attempted and mount_path:
        url = remount_uri
        if url and (not url.find('remount') > -1):
            del request.session[settings.REDIRECT_URL_SESSION_KEY]
    # just to be sure we have a url...
    if not url:
        url = reverse('storage-index')
    return redirect(url)

def storage_required( request ):
    """@storage_required redirects to this page if no storage available.
    """
    return render_to_response(
        'storage/required.html',
        {},
        context_instance=RequestContext(request, processors=[])
    )
