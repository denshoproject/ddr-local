# -*- coding: utf-8 -*-

from collections import OrderedDict
from copy import deepcopy
import json
import logging
logger = logging.getLogger(__name__)
import urlparse

from elasticsearch_dsl import Index, Search, A, Q, A
from elasticsearch_dsl.query import MultiMatch, Match
from elasticsearch_dsl.connections import connections
from elasticsearch_dsl.result import Result

from rest_framework.reverse import reverse

from django.conf import settings
from django.core.paginator import Paginator

from webui import docstore
from webui import identifier

# set default hosts and index
DOCSTORE = docstore.Docstore()


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
    
    def __init__(self, mappings, fields, search):
        self.mappings = mappings
        self.fields = fields
        self.s = search
    
    def prep(self, request_data):
        """
        searcher.prep(request_data)
        OR
        searcher.s = Search()
        """
        query = prep_query(
            text=request_data.get('fulltext', ''),
            must=request_data.get('must', []),
            should=request_data.get('should', []),
            mustnot=request_data.get('mustnot', []),
            aggs={},
        )
        logger.debug(json.dumps(query))
        if not query:
            raise Exception("Searcher.prep: Can't do an empty search. Give me something to work with here.")
        
        s = Search.from_dict(query)
        s = s.source(
            include=self.fields,
            exclude=[],
        )
        # doc_types
        doctype_names = None
        if isinstance(request_data.get('doctypes'), basestring):
            doctype_names = request_data['doctypes'].split(',')
        elif isinstance(request_data.get('doctypes'), list):
            doctype_names = request_data['doctypes']
        if not doctype_names:
            doctype_names = list(self.mappings.keys())
        doctypes = [self.mappings[d] for d in doctype_names]
        s = s.doc_type(','.join(doctype_names))

        if request_data.get('sort'):
            sorts = ','.join(request_data['sort'])
            s = s.sort(sorts)
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
                    
                    self.aggregations[field] = [
                        {
                            'key': bucket['key'],
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
    
        
def prep_query(text='', must=[], should=[], mustnot=[], aggs={}):
    """Assembles a dict conforming to the Elasticsearch query DSL.
    
    Elasticsearch query dicts
    See https://www.elastic.co/guide/en/elasticsearch/guide/current/_most_important_queries.html
    - {"match": {"fieldname": "value"}}
    - {"multi_match": {
        "query": "full text search",
        "fields": ["fieldname1", "fieldname2"]
      }}
    - {"terms": {"fieldname": ["value1","value2"]}},
    - {"range": {"fieldname.subfield": {"gt":20, "lte":31}}},
    - {"exists": {"fieldname": "title"}}
    - {"missing": {"fieldname": "title"}}
    
    Elasticsearch aggregations
    See https://www.elastic.co/guide/en/elasticsearch/guide/current/aggregations.html
    aggs = {
        'formats': {'terms': {'field': 'format'}},
        'topics': {'terms': {'field': 'topics'}},
    }
    
    >>> from DDR import docstore,format_json
    >>> t = 'posthuman'
    >>> a = [{'terms':{'language':['eng','chi']}}, {'terms':{'creators.role':['distraction']}}]
    >>> q = docstore.search_query(text=t, must=a)
    >>> print(format_json(q))
    >>> d = ['entity','segment']
    >>> f = ['id','title']
    >>> results = docstore.Docstore().search(doctypes=d, query=q, fields=f)
    >>> for x in results['hits']['hits']:
    ...     print x['_source']
    
    @param text: str Free-text search.
    @param must: list of Elasticsearch query dicts (see above)
    @param should:  list of Elasticsearch query dicts (see above)
    @param mustnot: list of Elasticsearch query dicts (see above)
    @param aggs: dict Elasticsearch aggregations subquery (see above)
    @returns: dict
    """
    assert isinstance(text, basestring)
    assert isinstance(must, list)
    assert isinstance(should, list)
    assert isinstance(mustnot, list)
    assert isinstance(aggs, dict)
    body = {
        'query': {},
    }
    if text or must or should or mustnot:
        body['query']['bool'] = {}
    if must:    body['query']['bool']['must'] = must
    if should:  body['query']['bool']['should'] = should
    if mustnot: body['query']['bool']['must_not'] = mustnot
    if text:
        if not body['query']['bool'].get('must'):
            body['query']['bool']['must'] = []
        body['query']['bool']['must'].append(
            {
                "match": {
                    "_all": text
                }
            }
        )
    if not body['query']:
        body['query'] = {"match_all": {}}
    if aggs:
        body['aggregations'] = aggs
    return body

def aggs_dict(aggregations):
    """Simplify aggregations data in search results
    
    input
    {
    u'format': {u'buckets': [{u'doc_count': 2, u'key': u'ds'}], u'doc_count_error_upper_bound': 0, u'sum_other_doc_count': 0},
    u'rights': {u'buckets': [{u'doc_count': 3, u'key': u'cc'}], u'doc_count_error_upper_bound': 0, u'sum_other_doc_count': 0},
    }
    output
    {
    u'format': {u'ds': 2},
    u'rights': {u'cc': 3},
    }
    """
    return {
        fieldname: {
            bucket['key']: str(bucket['doc_count'])
            for bucket in data['buckets']
        }
        for fieldname,data in list(aggregations.items())
    }
