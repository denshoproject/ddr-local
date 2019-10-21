import logging
logger = logging.getLogger(__name__)
import re
import urlparse

from django.conf import settings
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.http.request import HttpRequest
from django.shortcuts import render

from elasticsearch.exceptions import ConnectionError, ConnectionTimeout

from .. import api
from .. import forms_search as forms
from .. import models
from .. import search


def _mkurl(request, path, query=None):
    return urlparse.urlunparse((
        request.META['wsgi.url_scheme'],
        request.META.get('HTTP_HOST'),
        path, None, query, None
    ))

ID_PATTERNS = [
    '^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)-(?P<role>[a-zA-Z]+)-(?P<sha1>[\w]+)$',
    '^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)-(?P<sid>[\d]+)-(?P<role>[a-zA-Z]+)-(?P<sha1>[\w]+)$',
    '^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)-(?P<role>[a-zA-Z]+)$',
    '^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)-(?P<sid>[\d]+)-(?P<role>[a-zA-Z]+)$',
    '^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)-(?P<sid>[\d]+)$',
    '^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)$',
    '^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)$',
    #'^(?P<repo>[\w]+)-(?P<org>[\w]+)$',
    #'^(?P<repo>[\w]+)$',
]

def is_ddr_id(text, patterns=ID_PATTERNS):
    """True if text matches one of ID_PATTERNS
    
    See ddr-cmdln:DDR.identifier._is_id
    
    @param text: str
    @returns: dict of idparts including model
    """
    try:
        ddr_index = text.index('ddr')
    except:
        ddr_index = -1
    if ddr_index == 0:
        for pattern in patterns:
            m = re.match(pattern, text)
            if m:
                idparts = {k:v for k,v in m.groupdict().items()}
                return idparts
    return {}


# views ----------------------------------------------------

def search_ui(request):
    api_url = '%s?%s' % (
        _mkurl(request, reverse('api-search')),
        request.META['QUERY_STRING']
    )
    context = {
        'template_extends': 'ui/search/base.html',
        'hide_header_search': True,
        'searching': False,
        'filters': True,
        'api_url': api_url,
    }
    
    if request.GET.get('fulltext'):
        context['searching'] = True
        
        # Redirect if fulltext is a DDR ID
        if is_ddr_id(request.GET.get('fulltext')):
            return HttpResponseRedirect(
                reverse('ui-object-detail', args=[
                    request.GET.get('fulltext')
            ]))
        
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
        
        searcher = search.Searcher(conn=api.DOCSTORE)
        params = request.GET.copy()
        searcher.prepare(
            params=params,
            params_whitelist=search.SEARCH_PARAM_WHITELIST,
            search_models=search.SEARCH_MODELS,
            fields=search.SEARCH_INCLUDE_FIELDS,
            fields_nested=search.SEARCH_NESTED_FIELDS,
            fields_agg=search.SEARCH_AGG_FIELDS,
        )
        results = searcher.execute(limit, offset)
        form = forms.SearchForm(
            data=request.GET.copy(),
            search_results=results,
        )
        context['results'] = results
        context['search_form'] = form
        
        if results.objects:
            paginator = Paginator(
                results.ordered_dict(
                    request=request,
                    format_functions=models.FORMATTERS,
                    pad=True,
                )['objects'],
                results.page_size,
            )
            page = paginator.page(results.this_page)
            context['paginator'] = paginator
            context['page'] = page

    else:
        context['search_form'] = forms.SearchForm()

    return render(request, 'webui/search/results.html', context)
