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

from storage import STORAGE_MESSAGES
from storage import base_path, media_base_target, mount, unmount
from storage.forms import MountForm, UmountForm, ActiveForm



# helpers --------------------------------------------------------------

def get_unmounted(removables):
    unmounted = []
    for r in removables:
        ismounted = int(r.get('ismounted', '-1'))
        if not (ismounted == 1):
            unmounted.append(r)
    return unmounted


# views ----------------------------------------------------------------

def index( request ):
    """Interface for mounting/unmounting drives
    
    Saves label of most recently mounted drive in session.
    TODO THIS IS HORRIBLY INSECURE YOU ID10T!!!  >:^O
    """
    stat,removables = commands.removables()
    stat,mounted = commands.removables_mounted()
    unmounted = get_unmounted(removables)
    rdevices = [(d['devicefile'],d['label']) for d in unmounted]
    mdevices = [(d['mountpath'],d['devicefile']) for d in mounted]
    if request.method == 'POST':
        mount_form = MountForm(request.POST, devices=rdevices)
        umount_form = UmountForm(request.POST, devices=mdevices)
        which = request.POST.get('which','neither')
        if which == 'mount':
            if mount_form.is_valid():
                raw = mount_form.cleaned_data['device']
                devicefile,label = raw.split(' ',1)
                # do it
                mount(request, devicefile, label)
                return HttpResponseRedirect( reverse('storage-index') )
        elif which == 'umount':
            if umount_form.is_valid():
                raw = umount_form.cleaned_data['device']
                mountpoint,devicefile = raw.split(' ',1)
                # do it
                unmount(request, devicefile, mountpoint)
                return HttpResponseRedirect( reverse('storage-index') )
    else:
        rinitial = {}
        minitial = {}
        if len(rdevices) == 1:
            rinitial = { 'device': '{} {}'.format(rdevices[0][0], rdevices[0][1]) }
        if len(mdevices) == 1:
            minitial = { 'device': '{} {}'.format(mdevices[0][0], mdevices[0][1]) }
        mount_form = MountForm(devices=rdevices, initial=rinitial)
        umount_form = UmountForm(devices=mdevices, initial=minitial)
        # active device indicator/form
        ainitial = None
        mbase_target = media_base_target()
        if media_base_target():
            ainitial = {'device': os.path.dirname(media_base_target())}
        active_form = ActiveForm(devices=mdevices, initial=ainitial)
    return render_to_response(
        'storage/index.html',
        {'removables': removables,
         'unmounted': unmounted,
         'removables_mounted': mounted,
         'mount_form': mount_form,
         'umount_form': umount_form,
         'active_form': active_form,
         'remount_uri': request.session.get(settings.REDIRECT_URL_SESSION_KEY, None),
        },
        context_instance=RequestContext(request, processors=[])
    )

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
