import json
import os

import envoy
import requests



def identifier(path):
    """
    figure out the identifier for the given file
    """
    pass

def add_update(path, index, model):
    """
    curl -XPUT 'http://localhost:9200/ddr/collection/ddr-testing-141' -d '{ ... }'
    """
    if not os.path.exists(path):
        return 1
    headers = {'content-type': 'application/json'}
    with open(path, 'r') as f:
        data = json.loads(f.read())
    if not (data and data[1].get('id', None)):
        return 2
    cid = data[1]['id']
    url = 'http://localhost:9200/%s/%s/%s' % (index, model, cid)
    payload = {'d': data}
    r = requests.post(url, data=json.dumps(payload), headers=headers)
    return r.status_code

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

def paths(dirname):
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

def index(paths, index='ddr'):
    """
    for each JSON file in dir,
    if stale(), add_update()
    """
    for path in paths:
        if 'collection.json' in path:
            model = 'collection'
        elif 'entity.json' in path:
            model = 'object'
        elif ('master' in path) or ('mezzanine' in path):
            model = 'file'
        print(path)
        add_update(path, index=index, model=model)

def drop_all(index='ddr'):
    pass

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
    if data:
        hits = data['hits']['hits']
    return hits
