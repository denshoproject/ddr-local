import logging
logger = logging.getLogger(__name__)
import os

from django.core.cache import cache
from django.db import models

from ddrlocal.models import DDRLocalCollection


COLLECTION_FETCH_CACHE_KEY = 'webui:collection:%s:fetch'
COLLECTION_STATUS_CACHE_KEY = 'webui:collection:%s:status'
COLLECTION_ANNEX_STATUS_CACHE_KEY = 'webui:collection:%s:annex_status'

COLLECTION_FETCH_TIMEOUT = 0
COLLECTION_STATUS_TIMEOUT = 0
COLLECTION_ANNEX_STATUS_TIMEOUT = 0


class Collection( DDRLocalCollection ):
    
    def cache_delete( self ):
        cache.delete(COLLECTION_FETCH_CACHE_KEY % self.id)
        cache.delete(COLLECTION_STATUS_CACHE_KEY % self.id)
        cache.delete(COLLECTION_ANNEX_STATUS_CACHE_KEY % self.id)
    
    @staticmethod
    def from_json(collection_abs):
        """Instantiates a Collection object, loads data from collection.json.
        """
        collection = Collection(collection_abs)
        collection_uid = collection.id  # save this just in case
        collection.load_json(collection.json_path)
        if not collection.id:
            # id gets overwritten if collection.json is blank
            collection.id = collection_uid
        return collection
    
    def repo_fetch( self ):
        key = COLLECTION_FETCH_CACHE_KEY % self.id
        data = cache.get(key)
        if not data:
            data = super(Collection, self).repo_fetch()
            cache.set(key, data, COLLECTION_FETCH_TIMEOUT)
        return data
    
    def repo_status( self ):
        key = COLLECTION_STATUS_CACHE_KEY % self.id
        data = cache.get(key)
        if not data:
            data = super(Collection, self).repo_status()
            cache.set(key, data, COLLECTION_STATUS_TIMEOUT)
        return data
    
    def repo_annex_status( self ):
        key = COLLECTION_ANNEX_STATUS_CACHE_KEY % self.id
        data = cache.get(key)
        if not data:
            data = super(Collection, self).repo_annex_status()
            cache.set(key, data, COLLECTION_ANNEX_STATUS_TIMEOUT)
        return data
