from datetime import datetime
import logging
logger = logging.getLogger(__name__)
import os

from django.conf import settings
from django.contrib import messages
from django.core.context_processors import csrf
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import Http404, get_object_or_404, render_to_response
from django.template import RequestContext

from DDR import inventory
from DDR import natural_sort
from DDR.models import Organization, Store

from storage.decorators import storage_required
from webui.decorators import ddrview
from webui.forms import InventoryOpForm
from webui.tasks import inventory_clone, inventory_drop
from webui.views.decorators import login_required



# helpers --------------------------------------------------------------

def _inventory_org_path(repo, org):
    org_id = '{}-{}'.format(repo, org)
    path = os.path.join(settings.MEDIA_BASE, org_id)
    return path

def inventory_op( request, op, path, label, repo, org, cid, level, git_name, git_mail ):
    """clone collection into local store, update inventory.
    """
    if op in ['clone', 'drop']:
        collection_id = '-'.join([repo, org, cid])
        if op == 'clone':
            result = inventory_clone.apply_async( [path, label, repo, org, cid, level, git_name, git_mail], countdown=2)
            action = 'webui-inventory-clone'
        elif op == 'drop':
            result = inventory_drop.apply_async( [git_name, git_mail], countdown=2)
            action = 'webui-inventory-drop'
        celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
        # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
        task = {'task_id': result.task_id,
                'action': action,
                'collection_id': collection_id,
                'collection_url': '',
                'start': datetime.now().strftime(settings.TIMESTAMP_FORMAT),}
        celery_tasks[result.task_id] = task
        request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks


# views ----------------------------------------------------------------

INVENTORY_OPERATIONS = ['clone', 'drop']

@ddrview
@storage_required
def index( request ):
    """List Organizations present in this Store (e.g. in settings.MEDIA_BASE).
    """
    drive_label = inventory.guess_drive_label(settings.MEDIA_BASE)
    organizations = Organization.organizations(settings.MEDIA_BASE)
    return render_to_response(
        'webui/inventory/index.html',
        {'drive_label': drive_label,
         'organizations': organizations,},
        context_instance=RequestContext(request, processors=[])
    )

@ddrview
@storage_required
def detail( request, repo, org ):
    """List collection repos for this Organization, with add/remove links.
    
    Also added to list of collections: cid, status (present/not), and operation (clone/drop).
    """
    oid = '-'.join([repo, org])
    organization_path = _inventory_org_path(repo, org)
    if not os.path.exists(organization_path):
        raise Http404
    drive_label = inventory.guess_drive_label(settings.MEDIA_BASE)
    organization = Organization.load(organization_path)
    collections = []
    whereis = organization.whereis(server_url=settings.GITOLITE, server_location='digitalforest')
    whereis_keys = natural_sort(whereis.keys())
    for key in whereis_keys:
        if oid in key:
            repo,org,cid = key.split('-')
            present = False
            op = 'clone'
            for repos in whereis[key]:
                if repos['store'] == drive_label:
                    present = True
                    op = 'drop'
            collections.append( {'id':key, 'cid':cid, 'whereis':whereis[key], 'present':present, 'op':op,} )
    return render_to_response(
        'webui/inventory/detail.html',
        {'repo': repo,
         'org': org,
         'oid': oid,
         'drive_label': drive_label,
         'organization': organization,
         'collections': collections,
         },
        context_instance=RequestContext(request, processors=[])
    )

@ddrview
@login_required
@storage_required
def apply( request, repo, org, cid, op ):
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    oid = '-'.join([repo, org])
    collection_id = '-'.join([repo, org, cid])
    organization_path = _inventory_org_path(repo, org)
    drive_label = inventory.guess_drive_label(settings.MEDIA_BASE)
    organization = Organization.load(organization_path)
    if not organization:
        messages.error(request, 'Could not load inventory organization record!')
    if op not in INVENTORY_OPERATIONS:
        messages.error(request, "I'm sorry Dave, I'm afraid I can't do that")
    if request.method == 'POST':
        form = InventoryOpForm(request.POST)
        if form.is_valid():
            form_op = form.cleaned_data['op']
            if form_op == 'clone':
                inventory_op(request, 'clone', settings.MEDIA_BASE, drive_label,
                             repo, org, cid, 'meta', git_name, git_mail)
                messages.success(request, 'Cloning collection <b>%s</b>. Please wait a bit.' % collection_id)
            elif form_op == 'drop':
                messages.success(request, 'Dropping collection <b>%s</b>. Please wait a bit.' % collection_id)
            else:
                messages.success(request, 'Not sure what I\'m supposed to do here.')
            return HttpResponseRedirect( reverse('webui-inventory-detail', args=[repo,org]) )
    else:
        form = InventoryOpForm(data={'op':op})
    return render_to_response(
        'webui/inventory/apply.html',
        {'repo': repo,
         'org': org,
         'oid': oid,
         'collection_id': collection_id,
         'drive_label': drive_label,
         'organization': organization,
         'op': op,
         'form': form,},
        context_instance=RequestContext(request, processors=[])
    )
