import json
import logging
logger = logging.getLogger(__name__)
import os

import envoy
import requests

from django.conf import settings



def identifier(path):
    """
    figure out the identifier for the given file
    """
    pass

def add_update(path, index, model):
    """
    curl -XPUT 'http://localhost:9200/ddr/collection/ddr-testing-141' -d '{ ... }'
    """
    logger.debug('add_update(%s, %s, %s)' % (path, index, model))
    if not os.path.exists(path):
        return 1
    headers = {'content-type': 'application/json'}
    with open(path, 'r') as f:
        data = json.loads(f.read())
    
    # collections, entities
    if model in ['collection', 'entity', 'object']:
        if not (data and data[1].get('id', None)):
            return 2
        cid = None
        for field in data:
            if field.get('id',None):
                cid = field['id']
        url = 'http://localhost:9200/%s/%s/%s' % (index, model, cid)
    
    # files are different...
    elif model in ['file']:
        if not (data and data[1].get('path_rel', None)):
            return 2
        filename = None
        basename_orig = None
        label = None
        for field in data:
            if field.get('path_rel',None):
                filename,extension = os.path.splitext(field['path_rel'])
            if field.get('basename_orig', None):
                basename_orig = field['basename_orig']
            if field.get('label', None):
                label = field['label']
        if basename_orig and not label:
            label = basename_orig
        elif filename and not label:
            label = filename
        data.append({'id': filename})
        data.append({'title': label})
        url = 'http://localhost:9200/%s/%s/%s' % (index, model, filename)
    
    else:
        url = None
    if url:
        payload = {'d': data}
        r = requests.post(url, data=json.dumps(payload), headers=headers)
        return r.status_code
    return 3

def delete(index, model, id):
    """
    curl -XDELETE 'http://localhost:9200/twitter/tweet/1'
    """
    url = 'http://localhost:9200/%s/%s/%s' % (index, model, id)
    r = requests.delete(url)
    return r.status_code

def stale(path, identifier):
    """
    identifier(path)
    should we add/update?
    """
    return True

def metadata_files(dirname):
    """
    returns list of absolute paths to .json files in dirname.
    """
    paths = []
    excludes = ['tmp']
    for root, dirs, files in os.walk(dirname):
        for f in files:
            if f.endswith('.json'):
                path = os.path.join(root, f)
                exclude = [1 for x in excludes if x in path]
                if not exclude:
                    paths.append(path)
    return paths

def index(dirname, paths=None, index='ddr'):
    """
    for each JSON file in dir,
    if stale(), add_update()
    """
    logger.debug('index(%s, index="%s")' % (dirname, index))
    if not paths:
        paths = metadata_files(dirname)
    for path in paths:
        model = None
        if 'collection.json' in path:
            model = 'collection'
        elif 'entity.json' in path:
            model = 'object'
        elif ('master' in path) or ('mezzanine' in path):
            model = 'file'
        if path and index and model:
            add_update(path, index=index, model=model)
            logger.debug('%s: %s' % (model, path))
        else:
            logger.error('missing information!: %s' % path)
    logger.debug('INDEXING COMPLETED')

def delete_index(index):
    """
    curl -XDELETE 'http://localhost:9200/twitter/'
    """
    url = 'http://localhost:9200/%s/' % index
    r = requests.delete(url)
    return r.status_code

def index_exists(index='ddr'):
    """Indicates whether the given ElasticSearch index exists.
    curl -XHEAD 'http://localhost:9200/ddr/collection'
    """
    url = 'http://localhost:9200/%s' % index
    r = requests.head(url)
    if r.status_code == 200:
        return True
    return False

def model_exists(model):
    """Indicates whether an ElasticSearch 'type' exists for the given model.
    curl -XHEAD 'http://localhost:9200/ddr/collection'
    """
    url = 'http://localhost:9200/ddr/collection'
    r = requests.head(url)
    if r.status_code == 200:
        return True
    return False

def settings():
    """
    curl -XGET 'http://localhost:9200/twitter/_settings'
    """
    url = 'http://localhost:9200/_status'
    try:
        r = requests.get(url)
        data = json.loads(r.text)
    except:
        data = None
    return data

def status():
    """
    http://localhost:9200/_status
    """
    url = 'http://localhost:9200/_status'
    try:
        r = requests.get(url)
        data = json.loads(r.text)
    except:
        data = None
    return data

def query(index='ddr', model=None, query=None):
    """
    curl -XGET 'http://localhost:9200/twitter/tweet/_search?q=user:kimchy&pretty=true'
    """
    hits = []
    if model and query:
        url = 'http://localhost:9200/%s/%s/_search?q=%s&pretty=true' % (index, model, query)
    elif query:
        url = 'http://localhost:9200/%s/_search?q=%s&pretty=true' % (index, query)
    r = requests.get(url)
    data = json.loads(r.text)
    if data and data.get('hits', None):
        hits = data['hits']['hits']
    return hits
