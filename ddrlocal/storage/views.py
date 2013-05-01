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


# views ----------------------------------------------------------------


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
                if devicefile:
                    stat,unmounted = commands.umount(devicefile)
                if unmounted:
                    messages.success(request, 'Umounted {}'.format(value))
                elif unmounted == False:
                    messages.warning(request, 'Count not umount {}'.format(value))
                else:
                    messages.error(request, 'Problem unmounting {}: {},{}'.format(value, stat,unmounted))
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

def storage_required( request ):
    return render_to_response(
        'storage/required.html',
        {},
        context_instance=RequestContext(request, processors=[])
    )
