import logging
logger = logging.getLogger(__name__)

import redis
from django.conf import settings


def redis_flush_all():
    logger.debug('redis_flush_all()')
    #databases = [
    #    settings.REDIS_DB_CACHE,
    #    settings.REDIS_DB_CELERY_BROKER,
    #    settings.REDIS_DB_CELERY_RESULT,
    #    #settings.REDIS_DB_SORL,
    #]
    #for db in databases:
    #    r = redis.Redis(
    #        host=settings.REDIS_HOST,
    #        port=settings.REDIS_PORT,
    #        db=db
    #    )
    #    logger.debug(f'r {r}')
    #    result = r.flushall()
    #    #result = r.execute_command('FLUSHALL ASYNC')
    #    logger.debug(f'result {result}')

    #import subprocess
    #result = subprocess.check_output(['redis-cli','flushall'])
    #logger.debug(f'result {result}')

    import django_redis
    r = django_redis.get_redis_connection()
    logger.debug(f'r {r}')
    result = r.flushall()
    logger.debug(f'result {result}')
