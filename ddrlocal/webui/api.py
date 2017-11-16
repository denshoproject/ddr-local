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
    data['search'] = reverse('api-search', args=(), request=request)
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
    results = searcher.execute(limit, offset)
    data = results.ordered_dict(request, list_function=_prep_detail)
    return Response(data)


SEARCH_QUERY_FIELDS = [
    'fulltext',
    'topics',
    'facility',
    'language',
]

VOCAB_FIELDS = {
    'model': 'Model',
    'topics': 'Topics',
    'facility': 'Facility',
    'language': 'Language',
    'mimetype': 'Mimetype',
}

SEARCH_MODELS = ['repository','organization','collection','entity','file']

SEARCH_FIELDS = [
    'title',
    'label',
    'description',
]

@api_view(['GET'])
def search_form(request, format=None):
    return Response(
        #_search(request).ordered_dict(request)
        _search(request).ordered_dict(request, list_function=_prep_detail)
    )

def _search(request):
    """Search Page objects
    
    @param request: WSGIRequest
    @returns: search.SearchResults
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
        if key not in SEARCH_QUERY_FIELDS + ['page']
    ]
    for key in bad_fields:
        params.pop(key)
    
    if params.get('page'):
        thispage = int(params.pop('page')[-1])
    else:
        thispage = 0
    limit = request.GET.get('limit', int(request.GET.get('limit', settings.ELASTICSEARCH_MAX_SIZE)))
    offset = request.GET.get('offset', int(request.GET.get('offset', 0)))
    
    # build search object ------------------------
    
    s = elasticsearch_dsl.Search(
        using=DOCSTORE.es, index=DOCSTORE.indexname
    )
    for model in SEARCH_MODELS:
        s = s.doc_type(model)
    s = s.source(include=identifier.ELASTICSEARCH_LIST_FIELDS)
    
    if params.get('fulltext'):
        # MultiMatch chokes on lists
        fulltext = params.pop('fulltext')
        if isinstance(fulltext, list) and (len(fulltext) == 1):
            fulltext = fulltext[0]
        # fulltext search
        s = s.query(
            search.MultiMatch(
                query=fulltext,
                fields=SEARCH_FIELDS
            )
        )
    
    # filters
    for key,val in params.items():
        if key in SEARCH_QUERY_FIELDS:
            s = s.filter('terms', **{key: val})
    
    # aggregations
    for fieldname in VOCAB_FIELDS.keys():
        s.aggs.bucket(fieldname, 'terms', field=fieldname)
    
    # run search ---------------------------------
    
    searcher = search.Searcher(
        mappings=identifier.ELASTICSEARCH_CLASSES_BY_MODEL,
        fields=identifier.ELASTICSEARCH_LIST_FIELDS,
        search=s,
    )
    results = searcher.execute(limit, offset)
    #data = results.ordered_dict(request, list_function=_prep_detail)
    #return data
    return results


def _access_url(fi):
    """
    @param oi: (optional) file Identifier
    """
    return '%s%s%s' % (
        settings.MEDIA_URL,
        fi.path_abs().replace(settings.MEDIA_ROOT, ''),
        settings.ACCESS_FILE_SUFFIX,
    )

def image_present(fi):
    path = '%s%s' % (fi.path_abs(), settings.ACCESS_FILE_SUFFIX)
    return os.path.exists(path)

def _prep_detail(d, request, oi=None, is_list=False):
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

    img_url = ''
    if d.get('signature_id'):
        img_url = _access_url(identifier.Identifier(d['signature_id']))
    elif d.get('access_rel'):
        img_url = _access_url(oi)
    
    img_present = False
    if img_url:
        img_present = image_present(oi)
    
    data['id'] = d.pop('id')
    data['model'] = oi.model
    data['collection_id'] = collection_id
    
    data['links'] = OrderedDict()
    try:
        data['links']['html'] = reverse('webui-%s' % oi.model, args=([oi.id]), request=request)
    except NoReverseMatch:
        data['links']['html'] = ''
    data['links']['json'] = reverse('api-detail', args=[data['id']], request=request)

    if not is_list:
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
    data['img_present'] = img_present
    
    for key,val in d.items():
        if key not in DETAIL_EXCLUDE:
            data[key] = val
    return data
