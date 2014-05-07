from functools import wraps
import logging
logger = logging.getLogger(__name__)

from django.contrib import messages
from django.utils.decorators import available_attrs

from webui import set_docstore_index

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
        storage_label,docstore_index_exists = set_docstore_index(request)
        # feedback
        if storage_label and not docstore_index_exists:
            messages.warning(
                request,
                'No search index for %s. Search is disabled. Please reindex.' % (storage_label))
        if not (storage_label or docstore_index_exists):
            messages.warning(
                request,
                'Cound not find storage label. Search is disabled.')
        return func(request, *args, **kwargs)
    return inner
