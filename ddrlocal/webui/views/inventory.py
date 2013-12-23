import logging
logger = logging.getLogger(__name__)
import os

from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import Http404, get_object_or_404, render_to_response
from django.template import RequestContext

from DDR import inventory
from DDR import natural_sort
from DDR.models import Organization, Store

from storage.decorators import storage_required



# helpers --------------------------------------------------------------

def _inventory_org_path(repo, org):
    org_id = '{}-{}'.format(repo, org)
    path = os.path.join(settings.MEDIA_BASE, org_id)
    return path


# views ----------------------------------------------------------------

@storage_required
def detail( request, repo, org ):
    oid = '-'.join([repo, org])
    organization_path = _inventory_org_path(repo, org)
    drive_label = inventory.guess_drive_label(settings.MEDIA_BASE)
    organization = Organization.load(organization_path)
    if not organization:
        messages.error(request, 'Could not load inventory organization record!')
    store = organization.store(drive_label)
#    collections = organization.collections(server_url=settings.GITOLITE, server_location='digitalforest')
    collections = []
    whereis = organization.whereis(server_url=settings.GITOLITE, server_location='digitalforest')
    whereis_keys = natural_sort(whereis.keys())
    for key in whereis_keys:
        if oid in key:
            color = 'red'
            present = False
            for repos in whereis[key]:
                if repos['store'] == drive_label:
                    color = 'green'
                    present = True
            collections.append( {'cid':key, 'whereis':whereis[key], 'color':color, 'present':present,} )
    return render_to_response(
        'webui/inventory/detail.html',
        {'repo': repo,
         'org': org,
         'oid': oid,
         'drive_label': drive_label,
         'organization': organization,
         'store': store,
         'collections': collections,
#         'whereis': whereis,
#         'whereis_keys': whereis_keys,
         },
        context_instance=RequestContext(request, processors=[])
    )

def apply( request, repo, org, cid, op ):
    return render_to_response(
        'webui/inventory/apply.html',
        {},
        context_instance=RequestContext(request, processors=[])
    )
