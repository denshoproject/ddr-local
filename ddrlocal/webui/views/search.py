from datetime import datetime
from decimal import Decimal
import logging
logger = logging.getLogger(__name__)

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import Http404, get_object_or_404, render_to_response
from django.shortcuts import render
from django.template import RequestContext
from django.utils.http import urlquote  as django_urlquote

from elasticsearch import Elasticsearch

from DDR import converters
from DDR import models
from webui import api
from webui import docstore
from webui import forms
from webui import identifier
from webui import search
from webui import tasks
from webui.decorators import search_index
from webui.forms.search import SearchForm, IndexConfirmForm, DropConfirmForm
from webui.identifier import Identifier

BAD_CHARS = ('{', '}', '[', ']')


# helpers --------------------------------------------------------------

def kosher( query ):
    for char in BAD_CHARS:
        if char in query:
            return False
    return True

def massage_query_results( results, thispage, size ):
    objects = docstore.massage_query_results(results, thispage, size)
    results = None
    for o in objects:
        if not o.get('placeholder',False):
            o['absolute_url'] = Identifier(id=o['id']).absolute_url()
    return objects


# views ----------------------------------------------------------------

@search_index
def index( request ):
    ds = docstore.Docstore()
    if settings.DOCSTORE_INDEX in ds.aliases():
        target_index = ds.target_index(settings.DOCSTORE_INDEX)
    else:
        target_index = None
    return render_to_response(
        'webui/search/index.html',
        {'hide_header_search': True,
         'search_form': SearchForm,
         'docstore_index': settings.DOCSTORE_INDEX,
         'target_index': target_index,},
        context_instance=RequestContext(request, processors=[])
    )

@search_index
def results( request ):
    """Results of a search query or a DDR ID query.
    """
    ds = docstore.Docstore()
    if settings.DOCSTORE_INDEX in ds.aliases():
        target_index = ds.target_index(settings.DOCSTORE_INDEX)
    else:
        target_index = None
    template = 'webui/search/results.html'
    context = {
        'hide_header_search': True,
        'query': '',
        'error_message': '',
        'search_form': SearchForm(),
        'paginator': None,
        'page': None,
        'filters': None,
        'sort': None,
        'docstore_index': settings.DOCSTORE_INDEX,
        'target_index': target_index,
    }
    context['query'] = request.GET.get('query', '')
    # silently strip out bad chars
    query = context['query']
    for char in BAD_CHARS:
        query = query.replace(char, '')
        
    if query:
        context['search_form'] = SearchForm({'query': query})
        
        # prep query for elasticsearch
        model = request.GET.get('model', None)
        filters = {}
        fields = docstore.all_list_fields()
        sort = {'record_created': request.GET.get('record_created', ''),
                'record_lastmod': request.GET.get('record_lastmod', ''),}
        
        # do query and cache the results
        results = ds.search(
            query=query, filters=filters,
            model='collection,entity,file', fields=fields, sort=sort
        )
        if results.get('hits',None) and not results.get('status',None):
            # OK -- prep results for display
            thispage = request.GET.get('page', 1)
            objects = massage_query_results(results, thispage, settings.RESULTS_PER_PAGE)
            paginator = Paginator(objects, settings.RESULTS_PER_PAGE)
            page = paginator.page(thispage)
            context['paginator'] = paginator
            context['page'] = page
        else:
            # FAIL -- elasticsearch error
            context['error_message'] = 'Search query "%s" caused an error. Please try again.' % query
            return render_to_response(
                template, context, context_instance=RequestContext(request, processors=[])
            )
    
    return render_to_response(
        template, context, context_instance=RequestContext(request, processors=[])
    )


import urlparse

def _mkurl(request, path, query=None):
    return urlparse.urlunparse((
        request.META['wsgi.url_scheme'],
        request.META['HTTP_HOST'],
        path, None, query, None
    ))

@search_index
def search_ui(request):
    api_url = '%s?%s' % (
        _mkurl(request, reverse('api-search')),
        request.META['QUERY_STRING']
    )
    context = {
        'api_url': api_url,
    }

    if request.GET.get('fulltext'):

        if request.GET.get('offset'):
            # limit and offset args take precedence over page
            limit = request.GET.get('limit', int(request.GET.get('limit', settings.RESULTS_PER_PAGE)))
            offset = request.GET.get('offset', int(request.GET.get('offset', 0)))
        elif request.GET.get('page'):
            limit = settings.RESULTS_PER_PAGE
            thispage = int(request.GET['page'])
            offset = search.es_offset(limit, thispage)
        else:
            limit = settings.RESULTS_PER_PAGE
            offset = 0
        
        searcher = search.Searcher(
            mappings=identifier.ELASTICSEARCH_CLASSES_BY_MODEL,
            fields=identifier.ELASTICSEARCH_LIST_FIELDS,
        )
        searcher.prepare(request)
        results = searcher.execute(limit, offset)
        context['results'] = results
        context['search_form'] = forms.search.SearchForm(
            search_results=results,
            data=request.GET
        )
        
        if results.objects:
            paginator = Paginator(
                results.ordered_dict(
                    request=request, list_function=api._prep_detail, pad=True
                )['objects'],
                results.page_size,
            )
            context['paginator'] = paginator
            context['page'] = paginator.page(results.this_page)

    else:
        context['search_form'] = forms.search.SearchForm()
    
    return render(request, 'webui/search/search.html', context)
    
@search_index
def admin( request ):
    """Administrative stuff like re-indexing.
    """
    target_index = docstore.Docstore().target_index()
    server_info = []
    index_names = []
    indices = []
    es = Elasticsearch(hosts=settings.DOCSTORE_HOSTS)
    ping = es.ping()
    no_indices = True
    if ping:
        info = es.info()
        info_status = info['status']
        if info_status == 200:
            info_status_class = 'success'
        else:
            info_status_class = 'error'
        server_info.append( {'label':'status', 'data':info_status, 'class':info_status_class} )
        
        status = es.indices.status()
        shards_success = status['_shards']['successful']
        shards_failed = status['_shards']['failed']
        if shards_failed == 0:
            shards_success_class = 'success'
            shards_failed_class = 'success'
        else:
            shards_success_class = 'error'
            shards_failed_class = 'error'
        server_info.append( {'label':'shards(successful)', 'data':shards_success, 'class':shards_success_class} )
        server_info.append( {'label':'shards(failed)', 'data':shards_failed, 'class':shards_failed_class} )
        # indices
        for name in status['indices'].keys():
            no_indices = False
            server_info.append( {'label':name, 'data':'', 'class':''} )
            size = status['indices'][name]['total']['store']['size_in_bytes']
            ONEPLACE = Decimal(10) ** -1
            size_nice = Decimal(size/1024/1024.0).quantize(ONEPLACE)
            size_formatted = '%sMB (%s bytes)' % (size_nice, size)
            num_docs = status['indices'][name]['total']['docs']['num_docs']
            server_info.append( {'label':'size', 'data':size_formatted, 'class':'info'} )
            server_info.append( {'label':'documents', 'data':num_docs, 'class':'info'} )
            
            index_names.append(name)
            index = {'name':name, 'exists':True}
            indices.append(index)
    indexform = IndexConfirmForm(request=request)
    dropform = None
    if indices:
        dropform = DropConfirmForm(request=request)
    return render_to_response(
        'webui/search/admin.html',
        {'ping': ping,
         'no_indices': no_indices,
         'server_info': server_info,
         'indices': indices,
         'indexform': indexform,
         'dropform': dropform,
         'docstore_index': settings.DOCSTORE_INDEX,
         'target_index': target_index,},
        context_instance=RequestContext(request, processors=[])
    )

def reindex( request ):
    if request.method == 'POST':
        form = IndexConfirmForm(request.POST, request=request)
        if form.is_valid():
            index = form.cleaned_data['index']
            if index:
                result = tasks.reindex.apply_async( [index], countdown=2)
                # add celery task_id to session
                celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
                # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
                task = {'task_id': result.task_id,
                        'action': 'webui-search-reindex',
                        'index': index,
                        'start': converters.datetime_to_text(datetime.now(settings.TZ)),}
                celery_tasks[result.task_id] = task
                request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks
    return HttpResponseRedirect( reverse('webui-search-admin') )

def drop_index( request ):
    if request.method == 'POST':
        form = DropConfirmForm(request.POST, request=request)
        if form.is_valid():
            index = form.cleaned_data['index']
            ds = docstore.Docstore(index=index)
            ds.delete_index()
            messages.error(request,
                           'Search index "%s" dropped. ' \
                           'Click "Re-index" to reindex your collections.' % index)
    return HttpResponseRedirect( reverse('webui-search-admin') )
