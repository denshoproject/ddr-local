import logging
logger = logging.getLogger(__name__)

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import Http404, get_object_or_404, render_to_response
from django.template import RequestContext

from search import query

# helpers --------------------------------------------------------------


# views ----------------------------------------------------------------

def index( request ):
    model = request.GET.get('model', None)
    q = request.GET.get('query', None)
    hits = query(query=q)
    
    def rename(hit, fieldname):
        under = '_%s' % fieldname
        hit[fieldname] = hit.pop(under)
    
    for hit in hits:
        rename(hit, 'index')
        rename(hit, 'type')
        rename(hit, 'id')
        rename(hit, 'score')
        rename(hit, 'source')
        for field in hit['source']['d'][1:]:
            if field.keys():
                if field.keys()[0] == 'id': hit['id'] = field['id']
                if field.keys()[0] == 'title': hit['title'] = field['title']
        if hit.get('id', None):
            if hit['type'] == 'collection':
                repo,org,cid = hit['id'].split('-')
                hit['url'] = reverse('webui-collection', args=[repo,org,cid])
            elif hit['type'] == 'object':
                repo,org,cid,eid = hit['id'].split('-')
                hit['url'] = reverse('webui-entity', args=[repo,org,cid,eid])
    return render_to_response(
        'search/index.html',
        {'hits': hits,
         'query': q,},
        context_instance=RequestContext(request, processors=[])
    )
