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

    def _dict(self, params, data, format_functions, request=None, pad=False):
        """
        @param params: dict
        @param data: dict
        @param format_functions: dict
        @param pad: bool
        """
        data['total'] = self.total
        data['limit'] = self.limit
        data['offset'] = self.offset
        data['prev_offset'] = self.prev_offset
        data['next_offset'] = self.next_offset
        data['page_size'] = self.page_size
        data['this_page'] = self.this_page
        data['num_this_page'] = len(self.objects)
        if params.get('page'): params.pop('page')
        if params.get('limit'): params.pop('limit')
        if params.get('offset'): params.pop('offset')
        qs = [key + '=' + val for key,val in params.items()]
        query_string = '&'.join(qs)
        data['prev_api'] = ''
        data['next_api'] = ''
        data['objects'] = []
        data['query'] = self.query
        data['aggregations'] = self.aggregations
        
        # pad before
        if pad:
            data['objects'] += [{'n':n} for n in range(0, self.page_start)]
        # page
        for o in self.objects:
            format_function = format_functions[o.meta.index]
            data['objects'].append(
                format_function(
                    identifier.Identifier(o['id']),
                    o.to_dict(),
                    request,
                    is_detail=False,
                )
            )
        # pad after
        if pad:
            data['objects'] += [{'n':n} for n in range(self.page_next, self.total)]
        
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
        
        return data
