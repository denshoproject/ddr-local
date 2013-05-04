import logging
logger = logging.getLogger(__name__)
import os

from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import Http404, get_object_or_404, render_to_response
from django.template import RequestContext

from DDR import commands

from storage.forms import MountForm, UmountForm

# helpers --------------------------------------------------------------

def mount( request, devicefile, label ):
    mounted,mount_path = None,None
    if devicefile and label:
        stat,mount_path = commands.mount(devicefile, label)
    if mount_path:
        messages.success(request, 'Mounted {}'.format(label))
        # save label,mount_path in session
        request.session['storage_devicefile'] = devicefile
        request.session['storage_label'] = label
        request.session['storage_mount_path'] = mount_path
    elif mount_path == False:
        messages.warning(request, 'Count not mount {}'.format(label))
    else:
        messages.error(request, 'Problem mounting {}: {},{}'.format(label, stat,mounted))

def unmount( request, devicefile, value ):
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
        messages.success(request, 'Umounted {}'.format(value))
    elif unmounted == False:
        messages.warning(request, 'Count not umount {}'.format(value))
    else:
        messages.error(request, 'Problem unmounting {}: {},{}'.format(value, stat,unmounted))


# views ----------------------------------------------------------------


def index( request ):
    """Interface for mounting/unmounting drives
    
    Saves label of most recently mounted drive in session.
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
                # do it
                mount(request, devicefile, label)
                return HttpResponseRedirect( reverse('storage-index') )
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
                # do it
                unmount(request, devicefile, value)
                return HttpResponseRedirect( reverse('storage-index') )
    else:
        mount_form = MountForm()
        umount_form = UmountForm()
    return render_to_response(
        'storage/index.html',
        {'removables': removables,
         'removables_mounted': mounted,
         'mount_form': mount_form,
         'umount_form': umount_form,
        },
        context_instance=RequestContext(request, processors=[])
    )

def remount0( request, redirect=None ):
    """Show a spinning beachball while we try to remount the storage.
    This is just a static page that gives the user something to look at
    while remount1 is running.
    """
    redirect = request.session.get('remount_redirect_uri',None)
    try:
        del request.session['remount_redirect_uri']
    except KeyError:
        pass
    return render_to_response(
        'storage/remount.html',
        {'redirect': redirect,},
        context_instance=RequestContext(request, processors=[])
    )

def remount1( request, redirect=None ):
    """
    NOTES:
    Storage device's device file, label, and mount_path are stored in session
    on mount and removed from session on unmount.
    When the VM is suspended and resumed, the device often becomes available
    with a different device file (i.e. /dev/sdc1 instead of /dev/sdb1).
    The device is still mounted with the old device file.
    We need to unmount from the old device file and remount with the new
    device file that we get from looking directly at the system's device info.
    """
    redirect = request.session.get('remount_redirect_uri', 'webui-index')
    label = request.session.get('storage_label', None)
    # current "mounted" devicefile
    devicefile_session = request.session.get('storage_devicefile', None)
    # the actual new devicefile
    if label:
        stat,removables = commands.removables()
        for d in removables:
            if d['label'] == label:
                devicefile_udisks = d['devicefile']
    # unmount, mount
    if devicefile_session and label and devicefile_udisks:
        unmount(request, devicefile_session, label)
        mount(request, devicefile_udisks, label)
    return HttpResponseRedirect(reverse(redirect))

def storage_required( request ):
    return render_to_response(
        'storage/required.html',
        {},
        context_instance=RequestContext(request, processors=[])
    )
