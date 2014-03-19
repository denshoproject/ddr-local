from datetime import datetime
import logging
logger = logging.getLogger(__name__)

from dateutil import parser

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import Http404, get_object_or_404, render_to_response
from django.template import RequestContext

from DDR import docstore

from search import forms, tasks


# helpers --------------------------------------------------------------


# views ----------------------------------------------------------------

def index( request ):
    """Search forms, simple and advanced; links to admin
    """
    confirm = request.GET.get('confirm', None)
    if confirm:
        pass
        # start index task
        # message
        # redirect
    return render_to_response(
        'search/index.html',
        {},
        context_instance=RequestContext(request, processors=[])
    )

def query( request ):
    """Results of a search query.
    """
    # prep query for elasticsearch
    model = request.GET.get('model', None)
    q = request.GET.get('query', None)
    filters = {'public': request.GET.get('public', ''),
               'status': request.GET.get('status', ''),}
    sort = {'record_created': request.GET.get('record_created', ''),
            'record_lastmod': request.GET.get('record_lastmod', ''),}
    
    # do the query
    thispage = request.GET.get('page', 1)
    results = docstore.search(settings.DOCSTORE_HOSTS, settings.DOCSTORE_INDEX,
                              query=q, filters=filters,
                              fields=docstore.all_list_fields(), sort=sort)
    objects = docstore.massage_query_results(results, thispage, settings.RESULTS_PER_PAGE)
    results = None
    # urls for each record type
    for o in objects:
        if o.get('id', None) and o.get('type', None):
            if o['type'] == 'collection':
                repo,org,cid = o['id'].split('-')
                o['url'] = reverse('webui-collection', args=[repo,org,cid])
            elif o['type'] == 'entity':
                repo,org,cid,eid = o['id'].split('-')
                o['url'] = reverse('webui-entity', args=[repo,org,cid,eid])
            elif o['type'] == 'file':
                repo,org,cid,eid,role,sha1 = o['id'].split('-')
                o['url'] = reverse('webui-file', args=[repo,org,cid,eid,role,sha1])
    paginator = Paginator(objects, settings.RESULTS_PER_PAGE)
    page = paginator.page(thispage)
    return render_to_response(
        'search/query.html',
        {'paginator': paginator,
         'page': page,
         'query': q,
         'filters': filters,
         'sort': sort,},
        context_instance=RequestContext(request, processors=[])
    )

def admin( request ):
    """Administrative stuff like re-indexing.
    """
    status = docstore.status(settings.DOCSTORE_HOSTS)
    if status:
        status['shards'] = status.pop('_shards')
    
    confirm = request.GET.get('confirm', None)
    if confirm:
        pass
        # start index task
        # message
        # redirect
    indexform = forms.IndexConfirmForm()
    dropform = forms.DropConfirmForm()
    return render_to_response(
        'search/admin.html',
        {'status': status,
         'indexform': indexform,
         'dropform': dropform,},
        context_instance=RequestContext(request, processors=[])
    )

def reindex( request ):
    if request.method == 'POST':
        form = forms.IndexConfirmForm(request.POST)
        if form.is_valid():
            tasks.reindex_and_notify(request)
    return HttpResponseRedirect( reverse('search-admin') )

def drop_index( request ):
    if request.method == 'POST':
        form = forms.DropConfirmForm(request.POST)
        if form.is_valid():
            docstore.delete_index(settings.DOCSTORE_HOSTS, settings.DOCSTORE_INDEX)
            messages.error(request, 'Search indexes dropped. Click "Re-index" to reindex your collections.')
    return HttpResponseRedirect( reverse('search-admin') )
