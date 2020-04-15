import logging
import re


RE_STARTING_HTTP = re.compile('Starting new HTTP connection')
RE_CELERY_STATUS = re.compile('GET //celery/[0-9a-z-]+/status')

class SuppressCeleryNewConnections(logging.Filter):
    """Suppresses Celery's constant 'Starting new HTTP connection' messages.
    
    Celery writes two messages to the DEBUG logs every time task status is
    requested.  The webui notifications area updates task status every three
    seconds, which clutters up the logs. This filter suppresses these messages.
    
    Example:
        2013-08-29 10:01:42,517 INFO  connectionpool Starting new HTTP connection (1): 127.0.0.1
        2013-08-29 10:01:42,525 DEBUG connectionpool "GET //celery/44d64bbd-4235-4e3c-8a3c-792782de4b65/status HTTP/1.1" 200 None
    """

    def filter(self, record):
        logthis = 1
        mod_connectionpool = (record.module == 'connectionpool')
        msg_starting_http = None
        msg_celery_status = None
        if isinstance(record.msg, str):
            msg_starting_http = RE_STARTING_HTTP.search(record.msg)
            msg_celery_status = RE_CELERY_STATUS.search(record.msg)
        if mod_connectionpool and (msg_starting_http or msg_celery_status):
            logthis = 0
        return logthis
