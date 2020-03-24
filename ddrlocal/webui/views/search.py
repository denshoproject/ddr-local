from datetime import datetime
from decimal import Decimal
import logging
logger = logging.getLogger(__name__)
from urllib.parse import urlparse, urlunparse

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import Http404, render
from django.utils.http import urlquote  as django_urlquote

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError, ConnectionTimeout

from DDR import converters
from webui import api
from webui import docstore
from webui import forms
from webui import identifier
from webui import models
from webui import search
from webui.tasks import docstore as docstore_tasks
from webui.forms.search import SearchForm
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

def _mkurl(request, path, query=None):
    return urlunparse((
        request.META['wsgi.url_scheme'],
        request.META['HTTP_HOST'],
        path, None, query, None
    ))

def test_elasticsearch(request):
    try:
        health = search.DOCSTORE.health()
    except ConnectionError:
        return 'Could not connect to search engine: "%s"' % settings.DOCSTORE_HOSTS
    except ConnectionTimeout:
        return 'Connection to search engine timed out: "%s"' % settings.DOCSTORE_HOSTS
    return
    
def search_ui(request):
    elasticsearch_error = test_elasticsearch(request)
    if elasticsearch_error:
        return render(request, 'webui/search/error.html', {
            'message': elasticsearch_error,
        })
    
    api_url = '%s?%s' % (
        _mkurl(request, reverse('api-search')),
        request.META['QUERY_STRING']
    )
    context = {
        'api_url': api_url,
    }

    if request.GET.get('fulltext'):
        
        # Redirect if fulltext is a DDR ID
        try:
            ddr_index = text.index('ddr')
        except:
            ddr_index = -1
        if ddr_index == 0:
            try:
                oi = identifier.Identifier(request.GET.get('fulltext'))
                return HttpResponseRedirect(
                    reverse('webui-detail', args=[oi.id])
                )
            except:
                pass

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
        
        searcher = search.WebSearcher(
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
                    request=request, list_function=models.format_object, pad=True
                )['objects'],
                results.page_size,
            )
            context['paginator'] = paginator
            context['page'] = paginator.page(results.this_page)

    else:
        context['search_form'] = forms.search.SearchForm()
    
    return render(request, 'webui/search/search.html', context)
