from functools import wraps
import logging
logger = logging.getLogger(__name__)

from django.contrib import messages
from django.utils.decorators import available_attrs

from webui import set_docstore_index
from DDR.docstore import TransportError


def ddrview(f):
    """Clearly indicate in the logs that a view has started.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        r = args[0]  # request
        logging.debug('')
        logging.debug('========================================================================')
        logging.debug('{} {}'.format(r.META['REQUEST_METHOD'], r.META['PATH_INFO'], r.META['QUERY_STRING']))
        if r.META.get('HTTP_USER_AGENT', None):
            logging.debug('    {}'.format(r.META['HTTP_USER_AGENT']))
        logging.debug('{}.{}({}, {})'.format(f.__module__, f.__name__, args[1:], kwargs))
        return f(*args, **kwargs)
    return wrapper

def search_index(func):
    """Update active Elasticsearch index setting; alert if no active index.
    """
    @wraps(func, assigned=available_attrs(func))
    def inner(request, *args, **kwargs):
        s = ' '; d = ' '
        try:
            storage_label,docstore_index_exists = set_docstore_index(request)
        except TransportError:
            storage_label = 'e'
            docstore_index_exists = 'e'
        if storage_label and (storage_label == 'e'): s = 'e'
        elif storage_label: s = 's'
        if docstore_index_exists and (docstore_index_exists == 'e'): d = 'e'
        elif docstore_index_exists: d = 'd'
        key = ''.join([s,d])
        error_messages = {
            'sd': (None), # nothing to see here, move along
            's ': ('No search index for %s. Search is disabled. Please reindex.' % (storage_label)),
            ' d': ('No storage devices mounted. Search is disabled.'),
            '  ': ('No storage devices mounted and no search index. Search is disabled.'),
            'ee': ('Cannot connect to Elasticsearch. Search is disabled.'),
        }
        msg = error_messages[key]
        if msg:
            messages.warning(request, msg, extra_tags='bottom')
        return func(request, *args, **kwargs)
    return inner
