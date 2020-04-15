# -*- coding: utf-8 -*-

from collections import OrderedDict
import json
import os

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.reverse import reverse
from rest_framework.response import Response

from django.conf import settings

import elasticsearch_dsl

from webui import docstore
from webui import identifier
from webui.models import format_object, make_links
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
    data['links'] = make_links(oi, data, request, source='fs', is_detail=True)
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
    data = format_object(oi, d.to_dict(), request, is_detail=True)
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
    data = results.ordered_dict(list_function=format_object, request=request)
    return Response(data)


@api_view(['GET'])
def search_form(request, format=None):
    if request.GET.get('offset'):
        # limit and offset args take precedence over page
        limit = request.GET.get('limit', int(request.GET.get('limit', settings.RESULTS_PER_PAGE)))
        offset = request.GET.get('offset', int(request.GET.get('offset', 0)))
    elif request.GET.get('page'):
        limit = settings.RESULTS_PER_PAGE
        thispage = int(params.pop('page')[-1])
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
    return Response(
        results.ordered_dict(list_function=format_object, request=request)
    )
