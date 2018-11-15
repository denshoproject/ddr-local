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

        params = {key:val for key,val in request.GET.items()}
        if params.get('page'): params.pop('page')
        if params.get('limit'): params.pop('limit')
        if params.get('offset'): params.pop('offset')
        qs = [key + '=' + val for key,val in params.items()]
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
            key for key in params.keys()
            if key not in SEARCH_PARAM_WHITELIST + ['page']
        ]
        for key in bad_fields:
            params.pop(key)
        
        # doctypes
        if params.get('models'):
            models = params.pop('models')
        else:
            models = SEARCH_MODELS

        # TODO call parent class function here
        
        s = Search(
            using=DOCSTORE.es,
            index=DOCSTORE.indexname,
            doc_type=models,
        )
        s = s.source(include=identifier.ELASTICSEARCH_LIST_FIELDS)
        
        # fulltext query
        if params.get('fulltext'):
            # MultiMatch chokes on lists
            fulltext = params.pop('fulltext')
            if isinstance(fulltext, list) and (len(fulltext) == 1):
                fulltext = fulltext[0]
            # fulltext search
            s = s.query(
                QueryString(
                    query=fulltext,
                    fields=SEARCH_INCLUDE_FIELDS,
                    allow_leading_wildcard=False,
                )
            )

        # parent
        if params.get('parent'):
            param = params.pop('parent')
            parent = '%s*' % param[0]
            s = s.query("wildcard", id=parent)
        
        # filters
        for key,val in params.items():
            
            if key in SEARCH_NESTED_FIELDS:
    
                # search for *ALL* the topics (AND)
                for term_id in val:
                    s = s.filter(
                        Q('bool',
                          must=[
                              Q('nested',
                                path=key,
                                query=Q('term', **{'%s.id' % key: term_id})
                              )
                          ]
                        )
                    )
                
                ## search for *ANY* of the topics (OR)
                #s = s.query(
                #    Q('bool',
                #      must=[
                #          Q('nested',
                #            path=key,
                #            query=Q('terms', **{'%s.id' % key: val})
                #          )
                #      ]
                #    )
                #)
    
            elif key in SEARCH_PARAM_WHITELIST:
                s = s.filter('terms', **{key: val})
        
        # aggregations
        for fieldname,field in SEARCH_AGG_FIELDS.items():
            
            # nested aggregation (Elastic docs: https://goo.gl/xM8fPr)
            if fieldname == 'topics':
                s.aggs.bucket('topics', 'nested', path='topics') \
                      .bucket('topic_ids', 'terms', field='topics.id', size=1000)
            elif fieldname == 'facility':
                s.aggs.bucket('facility', 'nested', path='facility') \
                      .bucket('facility_ids', 'terms', field='facility.id', size=1000)
                # result:
                # results.aggregations['topics']['topic_ids']['buckets']
                #   {u'key': u'69', u'doc_count': 9}
                #   {u'key': u'68', u'doc_count': 2}
                #   {u'key': u'62', u'doc_count': 1}
            
            # simple aggregations
            else:
                s.aggs.bucket(fieldname, 'terms', field=field)
        
        self.s = s
