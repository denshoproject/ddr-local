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
        for line in d:
            if 'git_version' in line.keys():
                data['meta'] = line
            else:
                data[line.keys()[0]] = line.values()[0]
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
    data = _prep_detail(oi, d.to_dict(), request, is_detail=True)
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
    
    searcher = search.Searcher(
        mappings=identifier.ELASTICSEARCH_CLASSES_BY_MODEL,
        fields=identifier.ELASTICSEARCH_LIST_FIELDS,
        search=s,
    )
    results = searcher.execute(limit, offset)
    data = results.ordered_dict(request, list_function=_prep_detail)
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
    
    searcher = search.Searcher(
        mappings=identifier.ELASTICSEARCH_CLASSES_BY_MODEL,
        fields=identifier.ELASTICSEARCH_LIST_FIELDS,
    )
    searcher.prepare(request)
    results = searcher.execute(limit, offset)
    return Response(
        results.ordered_dict(request, list_function=_prep_detail)
    )

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
    return os.path.exists(
        '%s%s' % (fi.path_abs(), settings.ACCESS_FILE_SUFFIX)
    )

def make_links(oi, d, request, source='fs', is_detail=False):
    """Make the 'links pod' at the top of detail or list objects.
    
    @param oi: Identifier
    @param d: dict
    @param request: 
    @param source: str 'fs' (filesystem) or 'es' (elasticsearch)
    @param is_detail: boolean
    @returns: dict
    """
    assert source in ['fs', 'es']
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
    elif oi.model in ['repository','organization']:
        img_url = '%s%s/%s' % (
            settings.MEDIA_URL,
            oi.path_abs().replace(settings.MEDIA_ROOT, ''),
            'logo.png'
        )
    
    img_present = False
    if img_url:
        img_present = image_present(oi)
    
    links = OrderedDict()
    
    try:
        links['ui'] = reverse('webui-%s' % oi.model, args=([oi.id]), request=request)
    except NoReverseMatch:
        links['ui'] = ''
    
    links['api'] = reverse('api-%s-detail' % source, args=([oi.id]), request=request)
    
    # links to opposite
    if source == 'es':
        links['file'] = reverse('api-fs-detail', args=([oi.id]), request=request)
    elif source == 'fs':
        links['elastic'] = reverse('api-es-detail', args=([oi.id]), request=request)
    
    if is_detail:
        # objects above the collection level are stubs and do not have collection_id
        # collections have collection_id but have to point up to parent stub
        # API does not include stubs inside collections (roles)
        if collection_id and (collection_id != oi.id):
            parent_id = oi.parent_id(stubs=0)
        else:
            parent_id = oi.parent_id(stubs=1)
        if parent_id:
            links['parent'] = reverse('api-%s-detail' % source, args=[parent_id], request=request)
     
        if child_models:
            links['children'] = reverse('api-%s-children' % source, args=([oi.id]), request=request)
        else:
            links['children'] = ''

    links['img'] = img_url
    
    return links

def _prep_detail(oi, d, request, is_detail=False):
    """Format detail or list objects for API
    
    Certain fields are always included (id, title, etc and links).
    Everything else is determined by what fields are in the result dict.
    
    d is basically an elasticsearch_dsl.Result, packaged by search.SearchResults.
    
    @param d: dict
    @param request: 
    @param oi: (optional) Identifier
    """
    try:
        collection_id = oi.collection_id()
    except:
        collection_id = None
    
    data = OrderedDict()
    data['id'] = d.pop('id')
    data['model'] = oi.model
    data['collection_id'] = collection_id
    data['links'] = make_links(oi, d, request, source='es', is_detail=is_detail)
    for key,val in d.items():
        if key not in DETAIL_EXCLUDE:
            data[key] = val
    return data
