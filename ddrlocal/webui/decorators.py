from functools import wraps
import logging
logger = logging.getLogger(__name__)


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
