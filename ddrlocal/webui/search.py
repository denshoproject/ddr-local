# -*- coding: utf-8 -*-

from collections import OrderedDict
import logging
logger = logging.getLogger(__name__)

from django.conf import settings

from DDR.search import *
from webui import identifier


class WebSearchResults(SearchResults):

    def _make_prevnext_url(self, query, request):
        if request:
            return urlparse.urlunsplit([
                request.META['wsgi.url_scheme'],
                request.META['HTTP_HOST'],
                request.META['PATH_INFO'],
                query,
                None,
            ])
        return '?%s' % query
    
    def to_dict(self, list_function, request):
        """Express search results in API and Redis-friendly structure
        returns: dict
        """
        return self._dict({}, list_function, request)
    
    def ordered_dict(self, list_function, request, pad=False):
        """Express search results in API and Redis-friendly structure
        returns: OrderedDict
        """
        return self._dict(OrderedDict(), list_function, request, pad=pad)

    def _dict(self, data, list_function, request, pad=False):
        data['total'] = self.total
        data['limit'] = self.limit
        data['offset'] = self.offset
        data['prev_offset'] = self.prev_offset
        data['next_offset'] = self.next_offset
        data['page_size'] = self.page_size
        data['this_page'] = self.this_page

        params = {key:val for key,val in list(request.GET.items())}
        if params.get('page'): params.pop('page')
        if params.get('limit'): params.pop('limit')
        if params.get('offset'): params.pop('offset')
        qs = [key + '=' + val for key,val in list(params.items())]
        query_string = '&'.join(qs)

        data['prev_api'] = ''
        if self.prev_offset != None:
            data['prev_api'] = self._make_prevnext_url(
                u'%s&limit=%s&offset=%s' % (
                    query_string, self.limit, self.prev_offset
                ),
                request
            )
        data['next_api'] = ''
        if self.next_offset != None:
            data['next_api'] = self._make_prevnext_url(
                u'%s&limit=%s&offset=%s' % (
                    query_string, self.limit, self.next_offset
                ),
                request
            )
        data['objects'] = []
        
        # pad before
        if pad:
            data['objects'] += [
                {'n':n} for n in range(0, self.page_start)
            ]
        
        # page
        for o in self.objects:
            data['objects'].append(
                list_function(
                    identifier.Identifier(o['id']),
                    o.to_dict(),
                    request,
                    is_detail=False,
                )
            )
        
        # pad after
        if pad:
            data['objects'] += [
                {'n':n} for n in range(self.page_next, self.total)
            ]
        
        data['query'] = self.query
        data['aggregations'] = self.aggregations
        return data


class WebSearcher(Searcher):
    search_results_class = WebSearchResults

    def prepare(self, request):
        """assemble elasticsearch_dsl.Search object
        """

        # gather inputs ------------------------------
        
        if hasattr(request, 'query_params'):
            # api (rest_framework)
            params = dict(request.query_params)
        elif hasattr(request, 'GET'):
            # web ui (regular Django)
            params = dict(request.GET)
        else:
            params = {}
        
        # whitelist params
        bad_fields = [
            key for key in list(params.keys())
            if key not in SEARCH_PARAM_WHITELIST + ['page']
        ]
        for key in bad_fields:
            params.pop(key)
        
        fulltext = params.pop('fulltext')
        
        if params.get('models'):
            models = params.pop('models')
        else:
            models = SEARCH_MODELS
        
        parent = ''
        if params.get('parent'):
            parent = params.pop('parent')
            if isinstance(parent, list) and (len(parent) == 1):
                parent = parent[0]
            if parent:
                parent = '%s*' % parent
        
        # TODO call parent class function here
        super(WebSearcher, self).prepare(
            fulltext=fulltext,
            models=models,
            parent=parent,
            filters=params,
        )
