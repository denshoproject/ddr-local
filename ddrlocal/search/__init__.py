import json
import logging
logger = logging.getLogger(__name__)
import os

import envoy
import requests

from django.conf import settings




def _clean_dict(data):
    """Remove null or empty fields; ElasticSearch chokes on them.
    """
    if data and isinstance(data, dict):
        for key in data.keys():
            if not data[key]:
                del(data[key])
    
def _clean_payload(data):
    """Remove null or empty fields; ElasticSearch chokes on them.
    """
    # remove info about DDR release, git-annex version, etc
    if data and isinstance(data, list):
        data = data[1:]
        # remove empty fields
        for field in data:
            _clean_dict(field)

def add_update(index, model, path):
    """Add a new document to an index or update an existing one.
    
    curl -XPUT 'http://localhost:9200/ddr/collection/ddr-testing-141' -d '{ ... }'
    
    @param index: Name of the target index.
    @param model: Type of object ('collection', 'entity', 'file')
    @param path: Absolute path to the JSON file.
    @return 0 if successful, status code if not.
    """
    logger.debug('add_update(%s, %s, %s)' % (index, model, path))
    if not os.path.exists(path):
        return 1
    headers = {'content-type': 'application/json'}
    with open(path, 'r') as f:
        data = json.loads(f.read())
    _clean_payload(data)
    
    if model in ['collection', 'entity']:
        if not (data and data[1].get('id', None)):
            return 2
        cid = None
        for field in data:
            if field.get('id',None):
                cid = field['id']
        url = 'http://localhost:9200/%s/%s/%s' % (index, model, cid)
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
        payload = json.dumps({'d': data})
        logger.debug(url)
        logger.debug(payload)
        r = requests.put(url, data=payload, headers=headers)
        return r.status_code
    return 3

def delete(index, model, id):
    """
    curl -XDELETE 'http://localhost:9200/twitter/tweet/1'
    """
    url = 'http://localhost:9200/%s/%s/%s' % (index, model, id)
    r = requests.delete(url)
    return r.status_code

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

def index(index, dirname, paths=None):
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
            model = 'entity'
        elif ('master' in path) or ('mezzanine' in path):
            model = 'file'
        if path and index and model:
            add_update(index, model, path)
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

def index_exists(index):
    """Indicates whether the given ElasticSearch index exists.
    curl -XHEAD 'http://localhost:9200/ddr/collection'
    """
    url = 'http://localhost:9200/%s' % index
    r = requests.head(url)
    if r.status_code == 200:
        return True
    return False

def model_exists(index, model):
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

def query(index='ddr', model=None, query='', filters={}, sort=[]):
    """
    curl -XGET 'http://localhost:9200/twitter/tweet/_search?q=user:kimchy&pretty=true'
    """
    _clean_dict(filters)
    _clean_dict(sort)
    
    if model and query:
        url = 'http://localhost:9200/%s/%s/_search?q=%s&pretty=true' % (index, model, query)
    else:
        url = 'http://localhost:9200/%s/_search?q=%s&pretty=true' % (index, query)
    
    payload = {}
    if filters:
        payload['filter'] = {'term':filters}
    if sort:
        payload['sort'] = [sort]
    logger.debug(str(payload))
    
    headers = {'content-type': 'application/json'}
    r = requests.post(url, data=json.dumps(payload), headers=headers)
    data = json.loads(r.text)
    hits = []
    if data and data.get('hits', None):
        hits = data['hits']['hits']
    return hits
