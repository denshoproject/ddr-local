import logging
logger = logging.getLogger(__name__)

from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import Http404, get_object_or_404, render_to_response, redirect
from django.template import RequestContext

import storage
from storage.forms import StorageForm
from storage.tasks import mount_in_bkgnd


def index( request ):
    """Interface for mounting/unmounting drives and setting active device
    """
    devices = storage.devices()
    # device state
    for device in devices:
        device['state'] = []
        if device['mounted']:
            device['state'].append('mounted')
        if device['mounting']:
            device['state'].append('mounting')
        if device['linked']:
            device['state'].append('linked')
    # put form data for each action button in devices
    for device in devices:
        device['action_forms'] = []
        for action in device.get('actions'):
            form = {
                'url': reverse(
                    'storage-operation', args=(action, device['devicetype'],)),
                'action': action,
            }
            device['action_forms'].append(form)
    return render_to_response(
        'storage/index.html',
        {
            'devices': devices,
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
            basepath = form.cleaned_data['basepath']
            
            if opcode == 'mount':
                mount_in_bkgnd.apply_async((devicetype, devicefile,), countdown=2)
                status,msg = 0,'mounting'
                messages.success(request, 'Mounting device. Please be patient.')
            elif opcode == 'unmount':
                status,msg = storage.unmount(request, devicetype, devicefile)
            elif opcode == 'link':
                status,msg = storage.link(request, devicetype, basepath)
            elif opcode == 'unlink':
                status,msg = storage.unlink(request, devicetype, basepath)
            
            #if status == 'ok':
            #    messages.success(request, msg)
            #else:
            #    messages.warning(request, msg)
    
    return HttpResponseRedirect( reverse('storage-index') )

def storage_required( request ):
    """@storage_required redirects to this page if no storage available.
    """
    return render_to_response(
        'storage/required.html',
        {},
        context_instance=RequestContext(request, processors=[])
    )
