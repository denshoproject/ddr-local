# -*- coding: utf-8 -*-

from collections import OrderedDict
import json

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.reverse import reverse
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings
from django.core.urlresolvers import NoReverseMatch

import elasticsearch_dsl

from webui import docstore
from webui import identifier
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
    data['repository'] = reverse('api-detail', args=(['ddr']), request=request)
    return Response(data)

@api_view(['GET'])
def detail(request, oid, format=None):
    """OBJECT DETAIL DOCS
    """
    oi = identifier.Identifier(oid)
    d = docstore.Docstore().get(oi.model, oi.id)
    if not d:
        return Response(status=status.HTTP_404_NOT_FOUND)
    data = _prep_detail(d.to_dict(), request, oi=oi)
    return Response(data)

@api_view(['GET'])
def children(request, oid, limit=None, offset=None):
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
    # TODO where parent_id == oid
    #s = s.query('match_all')
    s = s.query("match", parent_id=oi.id)
    s = s.sort('sort', 'repo', 'org', 'cid', 'eid', 'role', 'sha1')
    s = s.source(include=identifier.ELASTICSEARCH_LIST_FIELDS)
    for model in child_models:
        s = s.doc_type(model)
    if not limit:
        limit = int(request.GET.get('limit', settings.ELASTICSEARCH_MAX_SIZE))
    if not offset:
        offset = int(request.GET.get('offset', 0))
    
    searcher = search.Searcher(
        mappings=identifier.ELASTICSEARCH_CLASSES_BY_MODEL,
        fields=identifier.ELASTICSEARCH_LIST_FIELDS,
        search=s,
    )
    query = s.to_dict()
    #assert False
    results = searcher.execute(limit, offset)
    #data = results.ordered_dict(request, list_fields=identifier.ELASTICSEARCH_LIST_FIELDS)
    data = results.ordered_dict(request, list_function=_prep_detail)
    return Response(data)


def _access_url(fi):
    """
    @param oi: (optional) file Identifier
    """
    return '%s%s%s' % (
        settings.MEDIA_URL,
        fi.path_abs().replace(settings.MEDIA_ROOT, ''),
        settings.ACCESS_FILE_SUFFIX,
    )

def _prep_detail(d, request, oi=None):
    """Format detail or list objects for API
    
    Certain fields are always included (id, title, etc and links).
    Everything else is determined by what fields are in the result dict.
    
    d is basically an elasticsearch_dsl.Result, packaged by search.SearchResults.
    
    @param d: dict
    @param request: 
    @param oi: (optional) Identifier
    """
    if not oi:
        oi = identifier.Identifier(d['id'])
    data = OrderedDict()
    try:
        collection_id = oi.collection_id()
        child_models = oi.child_models(stubs=False)
    except:
        collection_id = None
        child_models = oi.child_models(stubs=True)
    
    if d.get('signature_id'):
        img_url = _access_url(identifier.Identifier(d['signature_id']))
    elif d.get('access_rel'):
        img_url = _access_url(oi)
    else:
        img_url = ''
    
    data['id'] = d.pop('id')
    data['model'] = oi.model
    data['collection_id'] = collection_id
    
    data['links'] = OrderedDict()
    try:
        data['links']['html'] = reverse('webui-%s' % oi.model, args=([oi.id]), request=request)
    except NoReverseMatch:
        data['links']['html'] = ''
    data['links']['json'] = reverse('api-detail', args=[data['id']], request=request)
    
    # objects above the collection level are stubs and do not have collection_id
    # collections have collection_id but have to point up to parent stub
    # API does not include stubs inside collections (roles)
    if collection_id and (collection_id != oi.id):
        parent_id = oi.parent_id(stubs=0)
    else:
        parent_id = oi.parent_id(stubs=1)
    if parent_id:
        data['links']['parent'] = reverse('api-detail', args=[parent_id], request=request)

    if child_models:
        data['links']['children'] = reverse('api-children', args=[oi.id], request=request)
    else:
        data['links']['children'] = ''

    data['links']['img'] = img_url
    data['links']['thumb'] = ''

    for key,val in d.items():
        if key not in DETAIL_EXCLUDE:
            data[key] = val
    return data


def dict_list(obj, request):
    if hasattr(obj, 'to_dict_list'):
        return obj.to_dict_list(request=request)
    if isinstance(obj, dict) or isinstance(obj, OrderedDict):
        return obj
    elif isinstance(obj, elasticsearch_dsl.result.Result):
        assert False

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
        data['objects'].append(
            _prep_detail(o.to_dict(), request)
        )
        
    return data
