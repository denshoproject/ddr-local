# -*- coding: utf-8 -*-

from collections import OrderedDict
import json

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.reverse import reverse
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings

import elasticsearch_dsl

from webui import docstore
from webui import identifier
from DDR.identifier import ELASTICSEARCH_CLASSES
from DDR.identifier import ELASTICSEARCH_CLASSES_BY_MODEL

Repository = ELASTICSEARCH_CLASSES_BY_MODEL['repository']
Organization = ELASTICSEARCH_CLASSES_BY_MODEL['organization']
Collection = ELASTICSEARCH_CLASSES_BY_MODEL['collection']
Entity = ELASTICSEARCH_CLASSES_BY_MODEL['entity']
File = ELASTICSEARCH_CLASSES_BY_MODEL['file']

DOCSTORE = docstore.Docstore()

DETAIL_EXCLUDE = [
    'repo','org','cid','eid','sid','role','sha1',
    'id', 'model', 'collection_id',
]

LIST_INCLUDE = [
    'id', 'title', 'description', 'signature_id',
]


@api_view(['GET'])
def index(request, format=None):
    """INDEX DOCS
    """
    data = OrderedDict()
    data['collections'] = reverse('api-collections', request=request)
    data['search'] = reverse('api-search', request=request)
    return Response(data)


@api_view(['GET'])
def detail(request, oid, format=None):
    """OBJECT DETAIL DOCS
    """
    oi = identifier.Identifier(oid)
    d = docstore.Docstore().get(oi.model, oi.id)
    if not d:
        return Response(status=status.HTTP_404_NOT_FOUND)
    data = _prep_detail(oi, d.to_dict(), request)
    return Response(data)

def _prep_detail(oi, d, request):
    data = OrderedDict()
    data['model'] = oi.model
    data['id'] = d.pop('id')
    data['collection_id'] = d.get('collection_id')
    data['links'] = OrderedDict()
    data['links']['html'] = ''
    data['links']['json'] = reverse('api-detail', args=[data['id']], request=request)
    data['links']['img'] = ''
    data['links']['thumb'] = ''
    parent_id = oi.parent_id(stubs=1)
    if parent_id:
        data['links']['parent'] = reverse('api-detail', args=[parent_id], request=request)
    data['links']['children'] = reverse('api-children', args=[oi.id], request=request)
    for key,val in d.items():
        if key not in DETAIL_EXCLUDE:
            data[key] = val
    return data


@api_view(['GET'])
def children(request, oid, limit=None, offset=None):
    oi = identifier.Identifier(oid)
    
    s = elasticsearch_dsl.Search(
        using=DOCSTORE.es, index=DOCSTORE.indexname
    )
    s = s.query('match_all')
    s = s.sort('sort', 'repo', 'org', 'cid', 'eid', 'role', 'sha1')
    s = s.source(include=LIST_INCLUDE)
    for model in oi.child_models(stubs=1):
        s = s.doc_type(model)
    if not limit:
        limit = int(request.GET.get('limit', settings.ELASTICSEARCH_))
    if not offset:
        offset = int(request.GET.get('offset', 0))
    results = s.execute()
    
    data = _prep_children(oi, results, request)
    return Response(data)

def _prep_children(oi, results, request):
    data = OrderedDict()
    data['total'] = len(results.hits)
    data['page_size'] = 0
    data['prev'] = None
    data['next'] = None
    data['hits'] = []
    data['aggregations'] = {}
    data['objects'] = []
    for o in results.hits:
        oi = identifier.Identifier(o['id'])
        data['objects'].append(
            _prep_detail(oi, o.to_dict(), request)
        )
        
    return data


@api_view(['GET'])
def search(request, format=None):
    return Response()
