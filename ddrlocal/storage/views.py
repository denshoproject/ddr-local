import logging
logger = logging.getLogger(__name__)
import os

from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import Http404, get_object_or_404, render_to_response, redirect
from django.template import RequestContext

from DDR import commands

from storage import base_path
from storage import REMOUNT_POST_REDIRECT_URL_SESSION_KEY
from storage.forms import MountForm, UmountForm



# helpers --------------------------------------------------------------

def mount( request, devicefile, label ):
    if not (devicefile and label):
        messages.error(request, 'storage.mount(): devicefile or label missing [{} {}]'.format(devicefile, label))
        return None
    stat,mount_path = commands.mount(devicefile, label)
    if mount_path:
        messages.success(request, 'Mounted {}'.format(label))
        # save label,mount_path in session
        request.session['storage_devicefile'] = devicefile
        request.session['storage_label'] = label
        request.session['storage_mount_path'] = mount_path
        # write mount_path to cache
        bp = base_path(request)
    elif mount_path == False:
        messages.warning(request, 'Count not mount device [{} {}: {},{}]'.format(devicefile, label, stat,mount_path))
    else:
        messages.error(request, 'Problem mounting device [{} {}: {},{}]'.format(devicefile, label, stat,mount_path))
    return mount_path

def unmount( request, devicefile, label ):
    unmounted = None
    if devicefile:
        stat,unmounted = commands.umount(devicefile)
        # remove label,mount_path from session,
        # regardless of whether unmount worked
        try:
            del request.session['storage_devicefile']
            del request.session['storage_label']
            del request.session['storage_mount_path']
        except KeyError:
            pass
    if unmounted:
        messages.success(request, 'Umounted {}'.format(label))
    elif unmounted == False:
        messages.warning(request, 'Count not unmount device [{} {}: {},{}]'.format(devicefile, label, stat,mounted))
    else:
        messages.error(request, 'Problem unmounting device [{} {}: {},{}]'.format(devicefile, label, stat,mounted))
    return unmounted


# views ----------------------------------------------------------------


def index( request ):
    """Interface for mounting/unmounting drives
    
    Saves label of most recently mounted drive in session.
    TODO THIS IS HORRIBLY INSECURE YOU ID10T!!!  >:^O
    """
    stat,removables = commands.removables()
    stat,mounted = commands.removables_mounted()
    rdevices = [(d['devicefile'],d['label']) for d in removables]
    mdevices = [(d['mountpath'],d['devicefile']) for d in mounted]
    if request.method == 'POST':
        mount_form = MountForm(request.POST, devices=rdevices)
        umount_form = UmountForm(request.POST, devices=mdevices)
        which = request.POST.get('which','neither')
        if which == 'mount':
            if mount_form.is_valid():
                raw = mount_form.cleaned_data['device']
                devicefile,label = raw.split(' ')
                # do it
                mount(request, devicefile, label)
                return HttpResponseRedirect( reverse('storage-index') )
        elif which == 'umount':
            if umount_form.is_valid():
                raw = umount_form.cleaned_data['device']
                mountpoint,devicefile = raw.split(' ')
                # do it
                unmount(request, devicefile, mountpoint)
                return HttpResponseRedirect( reverse('storage-index') )
    else:
        mount_form = MountForm(devices=rdevices)
        umount_form = UmountForm(devices=mdevices)
    return render_to_response(
        'storage/index.html',
        {'removables': removables,
         'removables_mounted': mounted,
         'mount_form': mount_form,
         'umount_form': umount_form,
         'remount_uri': request.session.get(REMOUNT_POST_REDIRECT_URL_SESSION_KEY, None),
        },
        context_instance=RequestContext(request, processors=[])
    )

def remount0( request ):
    """Show a spinning beachball while we try to remount the storage.
    This is just a static page that gives the user something to look at
    while remount1 is running.
    """
    remount_uri = request.session.get(
        REMOUNT_POST_REDIRECT_URL_SESSION_KEY,
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
    remount_uri = request.session.get(REMOUNT_POST_REDIRECT_URL_SESSION_KEY, None)
    # device label
    label = request.session.get('storage_label', None)
    # current "mounted" devicefile
    devicefile_session = request.session.get('storage_devicefile', None)
    # the actual new devicefile
    devicefile_udisks = None
    if label:
        stat,removables = commands.removables()
        for d in removables:
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
        messages.warning(request, 'Unable to attempt remount. Please remount manually.')
    # redirect
    url = reverse('storage-index')
    if remount_attempted and mount_path:
        url = remount_uri
        if url and (not url.find('remount') > -1):
            del request.session[REMOUNT_POST_REDIRECT_URL_SESSION_KEY]
    return redirect(url)

def storage_required( request ):
    return render_to_response(
        'storage/required.html',
        {},
        context_instance=RequestContext(request, processors=[])
    )
