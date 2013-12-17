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

from search.tasks import reindex_and_notify
from storage import STORAGE_MESSAGES
from storage import base_path, media_base_target, removables, removables_mounted
from storage import mount, unmount, add_media_symlink, rm_media_symlink
from storage.forms import MountForm, UmountForm, ActiveForm, ManualSymlinkForm



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
    return [(d['mountpath'],d['devicefile']) for d in removables_mounted()]

def add_manual_symlink(devices):
    """Adds manually-set symlink to list of mounted devices if present.
    See storage.views.manual_symlink.
    """
    path = media_base_target()
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
    removablez = removables()
    mounted = removables_mounted()
    unmounted = get_unmounted(removablez)
    udevices = unmounted_devices()
    mdevices = mounted_devices()
    mdevices_plus_manual = add_manual_symlink(mdevices)
    media_target = media_base_target()
    #
    uinitial = {}
    minitial = {}
    ainitial = None
    if len(udevices) == 1:
        uinitial = { 'device': '{} {}'.format(udevices[0][0], udevices[0][1]) }
    if len(mdevices) == 1:
        minitial = { 'device': '{} {}'.format(mdevices[0][0], mdevices[0][1]) }
    for m in mdevices_plus_manual:
        if media_target and (m[0] in media_target):
            ainitial = {'device': m[0]}
    mount_form  = MountForm( devices=udevices, initial=uinitial)
    umount_form = UmountForm(devices=mdevices, initial=minitial)
    active_form = ActiveForm(devices=mdevices_plus_manual, initial=ainitial)
    manlink_form = ManualSymlinkForm()
    return render_to_response(
        'storage/index.html',
        {'removables': removablez,
         'unmounted': unmounted,
         'removables_mounted': mounted,
         'mount_form': mount_form,
         'umount_form': umount_form,
         'active_form': active_form,
         'manlink_form': manlink_form,
         'remount_uri': request.session.get(settings.REDIRECT_URL_SESSION_KEY, None),
        },
        context_instance=RequestContext(request, processors=[])
    )

def mount_device( request ):
    if request.method == 'POST':
        mount_form = MountForm(request.POST, devices=unmounted_devices())
        if mount_form.is_valid():
            raw = mount_form.cleaned_data['device']
            devicefile,label = raw.split(' ',1)
            mount(request, devicefile, label)
            # TODO regenerate redis caches
            # regenerate local ElasticSearch index
            reindex_and_notify(request)
    return HttpResponseRedirect( reverse('storage-index') )

def unmount_device( request ):
    if request.method == 'POST':
        umount_form = UmountForm(request.POST, devices=mounted_devices())
        if umount_form.is_valid():
            raw = umount_form.cleaned_data['device']
            mountpoint,devicefile = raw.split(' ',1)
            unmount(request, devicefile, mountpoint)
    return HttpResponseRedirect( reverse('storage-index') )

def activate_device( request ):
    if request.method == 'POST':
        active_form = ActiveForm(request.POST, devices=mounted_devices())
        if active_form.is_valid():
            path = active_form.cleaned_data['device']
            new_base_path = os.path.join(path, settings.DDR_USBHDD_BASE_DIR)
            rm_media_symlink()
            add_media_symlink(new_base_path)
            label = os.path.basename(path)
            messages.success(request, '<strong>%s</strong> is now the active device' % label)
            # TODO regenerate redis caches
            # regenerate local ElasticSearch index
            reindex_and_notify(request)
    return HttpResponseRedirect( reverse('storage-index') )

def manual_symlink( request ):
    """Sets the MEDIA_BASE symlink to an arbitrary path; used for browsing non-USB storage.
    """
    if request.method == 'POST':
        manlink_form = ManualSymlinkForm(request.POST)
        if manlink_form.is_valid():
            path = manlink_form.cleaned_data['path']
            rm_media_symlink()
            add_media_symlink(path)
            MB = settings.MEDIA_BASE
            if os.path.exists(MB) and os.path.islink(MB) and os.access(MB,os.W_OK):
                messages.success(request, '<strong>%s</strong> is now the active device.' % path)
            else:
                messages.error(request, 'Could not make <strong>%s</strong> the active device.' % path)
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
        messages.warning(request, STORAGE_MESSAGES['REMOUNT_FAIL'])
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
    return render_to_response(
        'storage/required.html',
        {},
        context_instance=RequestContext(request, processors=[])
    )
