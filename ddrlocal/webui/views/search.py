from datetime import datetime
import logging
logger = logging.getLogger(__name__)

from dateutil import parser

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import Http404, get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils.http import urlquote  as django_urlquote

from DDR import docstore, models
from webui.forms.search import SearchForm

BAD_CHARS = ('{', '}', '[', ']')


# helpers --------------------------------------------------------------

def kosher( query ):
    for char in BAD_CHARS:
        if char in query:
            return False
    return True


# views ----------------------------------------------------------------

def index( request ):
    return render_to_response(
        'webui/search/index.html',
        {'hide_header_search': True,
         'search_form': SearchForm,},
        context_instance=RequestContext(request, processors=[])
    )

def results( request ):
    """Results of a search query or a DDR ID query.
    """
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
        results = docstore.search(settings.DOCSTORE_HOSTS, settings.DOCSTORE_INDEX,
                                  query=query, filters=filters,
                                  fields=fields, sort=sort)
        
        if results.get('hits',None) and not results.get('status',None):
            # OK -- prep results for display
            thispage = request.GET.get('page', 1)
            #assert False
            objects = docstore.massage_query_results(results, thispage, settings.RESULTS_PER_PAGE)
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
