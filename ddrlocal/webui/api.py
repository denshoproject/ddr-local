# -*- coding: utf-8 -*-

from collections import OrderedDict
import json
import os

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.reverse import reverse
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings

import elasticsearch_dsl

from webui import docstore
from webui import identifier
from webui import models
from webui import search


DOCSTORE = docstore.Docstore()

Repository = identifier.ELASTICSEARCH_CLASSES_BY_MODEL['repository']
Organization = identifier.ELASTICSEARCH_CLASSES_BY_MODEL['organization']
Collection = identifier.ELASTICSEARCH_CLASSES_BY_MODEL['collection']
Entity = identifier.ELASTICSEARCH_CLASSES_BY_MODEL['entity']
File = identifier.ELASTICSEARCH_CLASSES_BY_MODEL['file']


DETAIL_EXCLUDE = [
    'repo','org','cid','eid','sid','role','sha1',
    'id', 'model', 'collection_id',
]


@api_view(['GET'])
def index(request, format=None):
    """INDEX DOCS
    """
    data = OrderedDict()
    data['browse (filesystem)'] = reverse('api-fs-detail', args=(['ddr']), request=request)
    data['browse (elasticsearch)'] = reverse('api-es-detail', args=(['ddr']), request=request)
    data['search (elasticsearch)'] = reverse('api-search', args=(), request=request)
    return Response(data)


@api_view(['GET'])
def fs_detail(request, oid, format=None):
    """Object detail (filesystem)
    """
    oi = identifier.Identifier(oid)
    if not os.path.exists(oi.path_abs('json')):
        return Response(status=status.HTTP_404_NOT_FOUND)
    
    data = OrderedDict()
    # these fields are always at the top
    data['id'] = oi.id
    data['model'] = oi.model
    try:
        data['collection_id'] = oi.collection_id()
    except:
        data['collection_id'] = None
    data['links'] = {}
    # everything else, we're rewriting the above fields but oh well
    with open(oi.path_abs('json'), 'r') as f:
        d = json.loads(f.read())
        # DDR object JSONs are lists of dicts
        if isinstance(d, list):
            for line in d:
                if 'git_version' in list(line.keys()):
                    data['meta'] = line
                else:
                    data[list(line.keys())[0]] = list(line.values())[0]
        # repository and organization JSON are just dicts
        elif isinstance(d, dict):
            for key,val in d.items():
                data[key] = val
    # didn't have the data we need before
    data['links'] = models.make_links(
        oi, data, request, source='fs', is_detail=True
    )
    return Response(data)

@api_view(['GET'])
def fs_children(request, oid, format=None):
    assert False


@api_view(['GET'])
def es_detail(request, oid, format=None):
    """Object detail (Elasticsearch)
    """
    oi = identifier.Identifier(oid)
    d = docstore.Docstore().get(oi.model, oi.id)
    if not d:
        return Response(status=status.HTTP_404_NOT_FOUND)
    data = models.format_object(oi, d.to_dict(), request, is_detail=True)
    return Response(data)

@api_view(['GET'])
def es_children(request, oid, limit=None, offset=None):
    oi = identifier.Identifier(oid)
    try:
        collection_id = oi.collection_id()
        child_models = oi.child_models(stubs=False)
    except:
        collection_id = None
        child_models = oi.child_models(stubs=True)
    
    s = elasticsearch_dsl.Search(
        using=DOCSTORE.es, index=DOCSTORE.indexname
    )
    s = s.query("match", parent_id=oi.id)
    s = s.sort('sort', 'repo', 'org', 'cid', 'eid', 'role', 'sha1')
    s = s.source(include=identifier.ELASTICSEARCH_LIST_FIELDS)
    for model in child_models:
        s = s.doc_type(model)
    if not limit:
        limit = int(request.GET.get('limit', settings.ELASTICSEARCH_MAX_SIZE))
    if not offset:
        offset = int(request.GET.get('offset', 0))
    
    searcher = search.WebSearcher(
        mappings=identifier.ELASTICSEARCH_CLASSES_BY_MODEL,
        fields=identifier.ELASTICSEARCH_LIST_FIELDS,
        search=s,
    )
    results = searcher.execute(limit, offset)
    data = results.ordered_dict(
        request=request,
        list_function=models.format_object,
    )
    return Response(data)


SEARCH_HELP_FULLTEXT = 'Search string using Elasticsearch query_string syntax.'
SEARCH_HELP_TOPICS   = 'Topic term ID(s) from http://partner.densho.org/vocab/api/0.2/topics.json.'
SEARCH_HELP_FACILITY = 'Facility ID(s) from http://partner.densho.org/vocab/api/0.2/facility.json.'
SEARCH_HELP_FORMAT   = 'Format term ID(s) from http://partner.densho.org/vocab/api/0.2/format.json.'
SEARCH_HELP_GENRE    = 'Genre term ID(s) from http://partner.densho.org/vocab/api/0.2/genre.json'
SEARCH_HELP_RIGHTS   = 'Rights term ID(s) from http://partner.densho.org/vocab/api/0.2/rights.json'
SEARCH_HELP_PAGE     = 'Selected results page (default: 0).'

class Search(APIView):
    
    #@swagger_auto_schema(manual_parameters=[
    #    openapi.Parameter(
    #        'fulltext',
    #        description=SEARCH_HELP_FULLTEXT,
    #        required=True,
    #        in_=openapi.IN_QUERY, type=openapi.TYPE_STRING
    #    ),
    #    openapi.Parameter(
    #        'topics',
    #        description=SEARCH_HELP_TOPICS,
    #        in_=openapi.IN_QUERY,
    #        type=openapi.TYPE_ARRAY, items={'type':'integer'}
    #    ),
    #    openapi.Parameter(
    #        'facility',
    #        description=SEARCH_HELP_FACILITY,
    #        in_=openapi.IN_QUERY,
    #        type=openapi.TYPE_ARRAY, items={'type':'integer'}
    #    ),
    #    openapi.Parameter(
    #        'format',
    #        description=SEARCH_HELP_FORMAT,
    #        in_=openapi.IN_QUERY,
    #        type=openapi.TYPE_ARRAY, items={'type':'string'}
    #    ),
    #    openapi.Parameter(
    #        'genre',
    #        description=SEARCH_HELP_GENRE,
    #        in_=openapi.IN_QUERY,
    #        type=openapi.TYPE_ARRAY, items={'type':'string'}
    #    ),
    #    openapi.Parameter(
    #        'rights',
    #        description=SEARCH_HELP_RIGHTS,
    #        in_=openapi.IN_QUERY,
    #        type=openapi.TYPE_ARRAY, items={'type':'string'}
    #    ),
    #    openapi.Parameter(
    #        'page',
    #        description=SEARCH_HELP_PAGE,
    #        in_=openapi.IN_QUERY, type=openapi.TYPE_STRING
    #    ),
    #])
    def get(self, request, format=None):
        """Search the Repository; good for simpler searches.
        
        Search API help: /api/0.2/search/help/
        """
        if request.GET.get('fulltext'):
            return self.grep(request)
        return Response({})
    
    #@swagger_auto_schema(manual_parameters=[
    #    openapi.Parameter(
    #        'body',
    #        description='DESCRIPTION HERE',
    #        required=True,
    #        in_=openapi.IN_FORM, type=openapi.TYPE_STRING),
    #])
    def post(self, request, format=None):
        """Search the Repository; good for more complicated custom searches.
        
        Search API help: /api/0.2/search/help/
        
        Sample search body JSON:
        
        {
            "fulltext": "seattle",
            "must": [
                {"topics": "239"}
            ]
        }

        """
        if request.data.get('fulltext'):
            return self.grep(request)
        return Response({})
    
    def grep(self, request):
        """DR search
        """
        def reget(request, field):
            if request.GET.get(field):
                return request.GET[field]
            elif request.data.get(field):
                return request.data[field]
            return None
        
        fulltext = reget(request, 'fulltext')
        offset = reget(request, 'offset')
        limit = reget(request, 'limit')
        page = reget(request, 'page')
        
        if offset:
            # limit and offset args take precedence over page
            if not limit:
                limit = settings.RESULTS_PER_PAGE
            offset = int(offset)
        elif page:
            limit = settings.RESULTS_PER_PAGE
            thispage = int(page)
            offset = search.es_offset(limit, thispage)
        else:
            limit = settings.RESULTS_PER_PAGE
            offset = 0
        
        searcher = search.Searcher()
        searcher.prepare(
            params=request.query_params.dict(),
            params_whitelist=search.SEARCH_PARAM_WHITELIST,
            search_models=search.SEARCH_MODELS,
            fields=search.SEARCH_INCLUDE_FIELDS,
            fields_nested=search.SEARCH_NESTED_FIELDS,
            fields_agg=search.SEARCH_AGG_FIELDS,
        )
        results = searcher.execute(limit, offset)
        results_dict = results.ordered_dict(
            request=request,
            format_functions=models.FORMATTERS,
        )
        results_dict.pop('aggregations')
        return Response(results_dict)


@api_view(['GET'])
def object_nodes(request, object_id):
    return files(request._request, object_id)

@api_view(['GET'])
def object_children(request, object_id):
    """OBJECT CHILDREN DOCS
    
    s - sort
    n - number of results AKA page size (limit)
    p - page (offset)
    """
    # TODO just get doc_type
    document = DOCSTORE.es.get(
        index=DOCSTORE.index_name(identifier.Identifier(object_id).model),
        id=object_id
    )
    model = document['_index'].replace(docstore.INDEX_PREFIX, '')
    if   model == 'repository': return organizations(request._request, object_id)
    elif model == 'organization': return collections(request._request, object_id)
    elif model == 'collection': return entities(request._request, object_id)
    elif model == 'entity': return segments(request._request, object_id)
    elif model == 'segment': return files(request._request, object_id)
    elif model == 'file': assert False
    raise Exception("Could not match ID,model,view.")

@api_view(['GET'])
def object_detail(request, object_id):
    """OBJECT DETAIL DOCS
    """
    # TODO just get doc_type
    document = DOCSTORE.es.get(
        index=DOCSTORE.index_name(identifier.Identifier(object_id).model),
        id=object_id
    )
    model = document['_index'].replace(docstore.INDEX_PREFIX, '')
    if   model == 'repository': return repository(request._request, object_id)
    elif model == 'organization': return organization(request._request, object_id)
    elif model == 'collection': return collection(request._request, object_id)
    elif model == 'entity': return entity(request._request, object_id)
    elif model == 'segment': return entity(request._request, object_id)
    elif model == 'file': return file(request._request, object_id)
    raise Exception("Could not match ID,model,view.")
