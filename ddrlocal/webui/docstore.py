from ssl import create_default_context

from django.conf import settings

from elasticsearch import Elasticsearch

from DDR import docstore

INDEX_PREFIX = 'ddr'


def get_elasticsearch():
    # TODO simplify this once everything is using SSL/passwords
    if settings.DOCSTORE_SSL_CERTFILE and settings.DOCSTORE_PASSWORD:
        context = create_default_context(cafile=settings.DOCSTORE_SSL_CERTFILE)
        context.check_hostname = False
        return Elasticsearch(
            settings.DOCSTORE_HOST,
            scheme='https', ssl_context=context,
            port=9200,
            http_auth=(settings.DOCSTORE_USERNAME, settings.DOCSTORE_PASSWORD),
        )
    elif settings.DOCSTORE_SSL_CERTFILE:
        context = create_default_context(cafile=settings.DOCSTORE_SSL_CERTFILE)
        context.check_hostname = False
        return Elasticsearch(
            settings.DOCSTORE_HOST,
            scheme='https', ssl_context=context,
            port=9200,
        )
    else:
        return Elasticsearch(
            settings.DOCSTORE_HOST,
            scheme='http',
            port=9200,
        )


class Docstore(docstore.Docstore):

    def __init__(self, hosts=settings.DOCSTORE_HOST):
        self.hosts = hosts
        self.es = get_elasticsearch()
