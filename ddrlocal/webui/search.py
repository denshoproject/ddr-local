# -*- coding: utf-8 -*-

from collections import OrderedDict
from copy import deepcopy
import json
import logging
logger = logging.getLogger(__name__)
import os
import urlparse

from elasticsearch_dsl import Index, Search, A, Q, A
from elasticsearch_dsl.query import MultiMatch, Match
from elasticsearch_dsl.connections import connections
from elasticsearch_dsl.result import Result

from rest_framework.reverse import reverse

from django.conf import settings
from django.core.paginator import Paginator

from DDR import vocab
from webui import docstore
from webui import identifier

# set default hosts and index
DOCSTORE = docstore.Docstore()


# whitelist of params recognized in URL query
# TODO move to ddr-defs/repo_models/elastic.py?
SEARCH_PARAM_WHITELIST = [
    'fulltext',
    'model',
    'models',
    'parent',
    'status',
    'public',
    'topics',
    'facility',
    'contributor',
    'creators',
    'format',
    'genre',
    'geography',
    'language',
    'location',
    'mimetype',
    'persons',
    'rights',
]

# fields where the relevant value is nested e.g. topics.id
# TODO move to ddr-defs/repo_models/elastic.py?
SEARCH_NESTED_FIELDS = [
    'facility',
    'topics',
]

# TODO move to ddr-defs/repo_models/elastic.py?
SEARCH_AGG_FIELDS = {
    'model': 'model',
    'status': 'status',
    'public': 'public',
    'contributor': 'contributor',
    'creators': 'creators.namepart',
    'facility': 'facility.id',
    'format': 'format',
    'genre': 'genre',
    'geography': 'geography.term',
    'language': 'language',
    'location': 'location',
    'mimetype': 'mimetype',
    'persons': 'persons',
    'rights': 'rights',
    'topics': 'topics.id',
}

# TODO move to ddr-defs/repo_models/elastic.py?
SEARCH_MODELS = ['repository','organization','collection','entity','file']

# fields searched by query e.g. query will find search terms in these fields
# TODO move to ddr-defs/repo_models/elastic.py?
SEARCH_INCLUDE_FIELDS = [
    'model',
    'status',
    'public',
    'title',
    'description',
    'contributor',
    'creators',
    'facility',
    'format',
    'genre',
    'geography',
    'label',
    'language',
    'location',
    'persons',
    'rights',
    'topics',
]

# TODO move to ddr-defs/repo_models/elastic.py?
SEARCH_FORM_LABELS = {
    'model': 'Model',
    'status': 'Status',
    'public': 'Public',
    'contributor': 'Contributor',
    'creators.namepart': 'Creators',
    'facility': 'Facility',
    'format': 'Format',
    'genre': 'Genre',
    'geography.term': 'Geography',
    'language': 'Language',
    'location': 'Location',
    'mimetype': 'Mimetype',
    'persons': 'Persons',
    'rights': 'Rights',
    'topics': 'Topics',
}

# TODO should this live in models?
def _vocab_choice_labels(field):
    return {
        str(term['id']): term['title']
        for term in vocab.get_vocab(
            '%s/%s.json' % (settings.VOCAB_TERMS_URL, field)
        )['terms']
    }
VOCAB_TOPICS_IDS_TITLES = {
    'facility': _vocab_choice_labels('facility'),
    'format': _vocab_choice_labels('format'),
    'genre': _vocab_choice_labels('genre'),
    'language': _vocab_choice_labels('language'),
    'public': _vocab_choice_labels('public'),
    'rights': _vocab_choice_labels('rights'),
    'status': _vocab_choice_labels('status'),
    'topics': _vocab_choice_labels('topics'),
}


def es_offset(pagesize, thispage):
    """Convert Django pagination to Elasticsearch limit/offset
    
    >>> es_offset(pagesize=10, thispage=1)
    0
    >>> es_offset(pagesize=10, thispage=2)
    10
    >>> es_offset(pagesize=10, thispage=3)
    20
    
    @param pagesize: int Number of items per page
    @param thispage: int The current page (1-indexed)
    @returns: int offset
    """
    page = thispage - 1
    if page < 0:
        page = 0
    return pagesize * page

def start_stop(limit, offset):
    """Convert Elasticsearch limit/offset to Python slicing start,stop
    
    >>> start_stop(10, 0)
    0,9
    >>> start_stop(10, 1)
    10,19
    >>> start_stop(10, 2)
    20,29
    """
    start = int(offset)
    stop = (start + int(limit)) - 1
    return start,stop
    
def django_page(limit, offset):
    """Convert Elasticsearch limit/offset pagination to Django page
    
    >>> django_page(limit=10, offset=0)
    1
    >>> django_page(limit=10, offset=10)
    2
    >>> django_page(limit=10, offset=20)
    3
    
    @param limit: int Number of items per page
    @param offset: int Start of current page
    @returns: int page
    """
    return divmod(offset, limit)[0] + 1


class Searcher(object):
    """
    >>> s = Searcher(index, mappings=DOCTYPE_CLASS, fields=SEARCH_LIST_FIELDS)
    >>> s.prep(request_data)
    'ok'
    >>> r = s.execute()
    'ok'
    >>> d = r.to_dict(request)
    """
    index = DOCSTORE.indexname
    mappings = {}
    fields = []
    q = OrderedDict()
    query = {}
    sort_cleaned = None
    s = None
    
    def __init__(self, mappings, fields, search=None):
        self.mappings = mappings
        self.fields = fields
        self.s = search

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
                MultiMatch(
                    query=fulltext,
                    fields=SEARCH_INCLUDE_FIELDS
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
    
    def execute(self, limit, offset):
        """Execute a query and return SearchResults
        
        @param limit: int
        @param offset: int
        @returns: SearchResults
        """
        if not self.s:
            raise Exception('Searcher has no ES Search object.')
        start,stop = start_stop(limit, offset)
        response = self.s[start:stop].execute()
        return SearchResults(
            mappings=self.mappings,
            query=self.s.to_dict(),
            results=response,
            limit=limit,
            offset=offset,
        )


class ESPaginator(Paginator):
    """
    Takes ES results automatically pads results
    """
    pass


class SearchResults(object):
    """Nicely packaged search results for use in API and UI.
    
    >>> from rg import search
    >>> q = {"fulltext":"minidoka"}
    >>> sr = search.run_search(request_data=q, request=None)
    """
    query = {}
    aggregations = None
    objects = []
    total = 0
    limit = settings.ELASTICSEARCH_MAX_SIZE
    offset = 0
    start = 0
    stop = 0
    prev_offset = 0
    next_offset = 0
    prev_api = u''
    next_api = u''
    page_size = 0
    this_page = 0
    prev_page = 0
    next_page = 0
    prev_html = u''
    next_html = u''
    errors = []

    def __init__(self, mappings, query={}, count=0, results=None, objects=[], limit=settings.ELASTICSEARCH_DEFAULT_LIMIT, offset=0):
        self.mappings = mappings
        self.query = query
        self.limit = int(limit)
        self.offset = int(offset)
        
        if results:
            # objects
            self.objects = [hit for hit in results]
            if results.hits.total:
                self.total = int(results.hits.total)

            # aggregations
            self.aggregations = {}
            if hasattr(results, 'aggregations'):
                results_aggregations = results.aggregations
                for field in results.aggregations.to_dict().keys():
                    
                    # nested aggregations
                    if field == 'topics':
                        buckets = results.aggregations['topics']['topic_ids'].buckets
                    elif field == 'facility':
                        buckets = results.aggregations['facility']['facility_ids'].buckets
                    # simple aggregations
                    else:
                        buckets = results.aggregations[field].buckets

                    if VOCAB_TOPICS_IDS_TITLES.get(field):
                        self.aggregations[field] = []
                        for bucket in buckets:
                            if bucket['key'] and bucket['doc_count']:
                                self.aggregations[field].append({
                                    'key': bucket['key'],
                                    'label': VOCAB_TOPICS_IDS_TITLES[field].get(str(bucket['key'])),
                                    'doc_count': str(bucket['doc_count']),
                                })
                                # print topics/facility errors in search results
                                # TODO hard-coded
                                if (field in ['topics', 'facility']) and not (isinstance(bucket['key'], int) or bucket['key'].isdigit()):
                                    self.errors.append(bucket)

                    else:
                        self.aggregations[field] = [
                            {
                                'key': bucket['key'],
                                'label': bucket['key'],
                                'doc_count': str(bucket['doc_count']),
                            }
                            for bucket in buckets
                            if bucket['key'] and bucket['doc_count']
                        ]

        elif objects:
            # objects
            self.objects = objects
            self.total = len(objects)

        else:
            self.total = count

        # elasticsearch
        self.prev_offset = self.offset - self.limit
        self.next_offset = self.offset + self.limit
        if self.prev_offset < 0:
            self.prev_offset = None
        if self.next_offset >= self.total:
            self.next_offset = None

        # django
        self.page_size = self.limit
        self.this_page = django_page(self.limit, self.offset)
        self.prev_page = u''
        self.next_page = u''
        # django pagination
        self.page_start = (self.this_page - 1) * self.page_size
        self.page_next = self.this_page * self.page_size
        self.pad_before = range(0, self.page_start)
        self.pad_after = range(self.page_next, self.total)
    
    def __repr__(self):
        return u"<SearchResults '%s' [%s]>" % (
            self.query, self.total
        )

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
    
    def to_dict(self, request, list_function):
        """Express search results in API and Redis-friendly structure
        returns: dict
        """
        return self._dict({}, request, list_function)
    
    def ordered_dict(self, request, list_function, pad=False):
        """Express search results in API and Redis-friendly structure
        returns: OrderedDict
        """
        return self._dict(OrderedDict(), request, list_function, pad=pad)
    
    def _dict(self, data, request, list_function, pad=False):
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
                u'%s&limit=%s&offset=%s' % (query_string, self.limit, self.prev_offset),
                request
            )
        data['next_api'] = ''
        if self.next_offset != None:
            data['next_api'] = self._make_prevnext_url(
                u'%s&limit=%s&offset=%s' % (query_string, self.limit, self.next_offset),
                request
            )
        data['objects'] = []
        
        # pad before
        if pad:
            data['objects'] += [{'n':n} for n in range(0, self.page_start)]
        
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
            data['objects'] += [{'n':n} for n in range(self.page_next, self.total)]
        
        data['query'] = self.query
        data['aggregations'] = self.aggregations
        return data
