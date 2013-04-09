import os

from django.conf import settings
from django.core.context_processors import csrf
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import Http404, get_object_or_404, render_to_response
from django.template import RequestContext

import envoy


def login(request):
    return render_to_response(
        'webui/login.html',
        {},
        context_instance=RequestContext(request, processors=[])
    )

def logout(request):
    return render_to_response(
        'webui/logout.html',
        {},
        context_instance=RequestContext(request, processors=[])
    )

def collections(request):
    collections = []
    cmd = 'collection clocal --base={} --repository={} --organization={}'.format(
        settings.DDR_BASE_PATH, settings.DDR_REPOSITORY, settings.DDR_ORGANIZATION)
    run = envoy.run(cmd)
    if run.std_out:
        colls = run.std_out.split('\n')
    for c in colls:
        if c:
            repo,org,cid = c.split('-')
            collections.append( (c,repo,org,cid) )
    return render_to_response(
        'webui/collections.html',
        {'collections': collections,},
        context_instance=RequestContext(request, processors=[])
    )

def collection(request, repo, org, cid):
    collection_uid = '{}-{}-{}'.format(repo, org, cid)
    collection_path = os.path.join(settings.DDR_BASE_PATH,collection_uid)
    # ead
    ead_path = os.path.join(collection_path, 'ead.xml')
    ef = open(ead_path,'r')
    ead = ef.read()
    # status
    status_cmd = 'collection status --collection={}'.format(collection_path)
    run = envoy.run(status_cmd)
    if run.std_out:
        status = run.std_out
    # annex status
    astatus_cmd = 'collection astatus --collection={}'.format(collection_path)
    run = envoy.run(astatus_cmd)
    if run.std_out:
        astatus = run.std_out
    return render_to_response(
        'webui/collection.html',
        {'collection_uid': collection_uid,
         'ead': ead,
         'status': status,
         'astatus': astatus,},
        context_instance=RequestContext(request, processors=[])
    )

