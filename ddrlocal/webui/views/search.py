import logging
logger = logging.getLogger(__name__)
import re
from urllib.parse import urlparse, urlunparse

from django.conf import settings
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.http.request import HttpRequest
from django.shortcuts import render

from elasticsearch.exceptions import ConnectionError, ConnectionTimeout

from .. import api
from ..forms import search as forms
from .. import models
from .. import search
from ..decorators import ui_state


def _mkurl(request, path, query=None):
    return urlunparse((
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

def limit_offset(request):
    if request.GET.get('offset'):
        # limit and offset args take precedence over page
        limit = request.GET.get(
            'limit', int(request.GET.get('limit', settings.RESULTS_PER_PAGE))
        )
        offset = request.GET.get('offset', int(request.GET.get('offset', 0)))
    elif request.GET.get('page'):
        limit = settings.RESULTS_PER_PAGE
        thispage = int(request.GET['page'])
        offset = search.es_offset(limit, thispage)
    else:
        limit = settings.RESULTS_PER_PAGE
        offset = 0
    return limit,offset


# views ----------------------------------------------------

@ui_state
def search_ui(request):
    api_url = '%s?%s' % (
        _mkurl(request, reverse('api-search')),
        request.META['QUERY_STRING']
    )
    context = {
        'template_extends': 'webui/search/base.html',
        'hide_header_search': True,
        'searching': False,
        'filters': True,
        'api_url': api_url,
    }
    
    searcher = search.Searcher()
    if request.GET.get('fulltext'):
        # Redirect if fulltext is a DDR ID
        if is_ddr_id(request.GET.get('fulltext')):
            return HttpResponseRedirect(
                reverse('webui-detail', args=[
                    request.GET.get('fulltext')
            ]))
        params = request.GET.copy()
        searcher.prepare(
            params=params,
            params_whitelist=search.SEARCH_PARAM_WHITELIST,
            search_models=search.SEARCH_MODELS,
            fields=search.SEARCH_INCLUDE_FIELDS,
            fields_nested=search.SEARCH_NESTED_FIELDS,
            fields_agg=search.SEARCH_AGG_FIELDS,
        )
        context['searching'] = True
    
    if searcher.params.get('fulltext'):
        limit,offset = limit_offset(request)
        results = searcher.execute(limit, offset)
        paginator = Paginator(
            results.ordered_dict(
                request=request,
                format_functions=models.FORMATTERS,
                pad=True,
            )['objects'],
            results.page_size,
        )
        page = paginator.page(results.this_page)
        
        form = forms.SearchForm(
            data=request.GET.copy(),
            search_results=results,
        )
        
        context['results'] = results
        context['paginator'] = paginator
        context['page'] = page
        context['search_form'] = form

    else:
        form = forms.SearchForm(
            data=request.GET.copy(),
        )
        context['search_form'] = forms.SearchForm()

    return render(request, 'webui/search/results.html', context)

def collection(request, oid):
    #filter_if_branded(request, i)
    collection = models.Collection.get(oid, request)
    if not collection:
        raise Http404
    return parent_search(request, collection)

def facetterm(request, facet_id, term_id):
    oid = '-'.join([facet_id, term_id])
    term = models.Term.get(oid, request)
    if not term:
        raise Http404
    return parent_search(request, term)

def narrator(request, oid):
    narrator = models.Narrator.get(oid, request)
    if not narrator:
        raise Http404
    return parent_search(request, narrator)

@ui_state
def parent_search(request, obj):
    """search within collection/facetterm/narrator
    """
    api_url = '%s?%s' % (
        _mkurl(request, reverse('api-search')),
        request.META['QUERY_STRING']
    )
    this_url = reverse('ui-search-results')
    template = 'webui/search/results.html'
    template_extends = "ui/search/base.html"
    context = {
        'hide_header_search': True,
        'searching': False,
        'filters': True,
        'api_url': api_url,
    }

    params = request.GET.copy()
    limit,offset = limit_offset(request)
    params['parent'] = obj['id']
    search_models = search.SEARCH_MODELS
    
    # search collection
    if obj['model'] == 'collection':
        search_models = ['ddrentity', 'ddrsegment']
        this_url = reverse('ui-search-collection', args=[obj['id']])
        template_extends = "ui/collections/base.html"
    # search topic
    elif (obj['model'] == 'ddrfacetterm') and (obj['facet'] == 'topics'):
        this_url = reverse('ui-search-facetterm', args=[obj['facet'], obj['term_id']])
        template_extends = "ui/facets/base-topics.html"
        obj['model'] = 'topics'
    # search facility
    elif (obj['model'] == 'ddrfacetterm') and (obj['facet'] == 'facility'):
        this_url = reverse('ui-search-facetterm', args=[obj['facet'], obj['term_id']])
        template_extends = "ui/facets/base-facility.html"
        obj['model'] = 'facilities'
    # search narrator
    elif obj['model'] == 'narrator':
        search_models = ['ddrentity', 'ddrsegment']
        this_url = reverse('ui-search-narrator', args=[obj['id']])
        template_extends = "ui/narrators/base.html"
        obj['title'] = obj['display_name']
    context['template_extends'] = template_extends
    context['object'] = obj

    searcher = search.Searcher()
    searcher.prepare(
        params=params,
        params_whitelist=search.SEARCH_PARAM_WHITELIST,
        search_models=search_models,
        fields=search.SEARCH_INCLUDE_FIELDS,
        fields_nested=search.SEARCH_NESTED_FIELDS,
        fields_agg=search.SEARCH_AGG_FIELDS,
    )
    results = searcher.execute(limit, offset)
    paginator = Paginator(
        results.ordered_dict(
            request=request,
            format_functions=models.FORMATTERS,
            pad=True,
        )['objects'],
        results.page_size,
    )
    page = paginator.page(results.this_page)
    form = forms.SearchForm(
        data=params,
        search_results=results,
    )
    context['results'] = results
    context['search_form'] = form
    context['paginator'] = paginator
    context['page'] = page

    return render(request, 'webui/search/results.html', context)
