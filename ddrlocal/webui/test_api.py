from elasticsearch.connection.base import TransportError
import pytest
import requests

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

HOST_CHECK_URL = 'http://{}'.format(settings.DOCSTORE_HOST)

NO_ELASTICSEARCH_ERR = "Elasticsearch cluster not available."
def no_elasticsearch():
    """Returns True if cannot contact cluster; use to skip tests
    """
    try:
        r = requests.get(HOST_CHECK_URL, timeout=1)
        if r.status_code == 200:
            return False
    except ConnectionError:
        print('ConnectionError')
        return True
    except TransportError:
        print('TransportError')
        return True
    return True


class OpenAPISchemaView(TestCase):

    def test_schema(self):
        response = self.client.get(reverse('openapi-schema'))
        self.assertEqual(response.status_code, 200)


class APIIndexView(TestCase):

    def test_index(self):
        response = self.client.get(reverse('api-index'))
        self.assertEqual(response.status_code, 200)


class APIObjectViewsFS(TestCase):

    def test_api_fs_repository(self):
        oid = 'ddr'
        response = self.client.get(reverse('api-fs-detail', args=[oid]))
        self.assertEqual(response.status_code, 200)

    #def test_api_fs_repository_children(self):
    #    oid = 'ddr'
    #    response = self.client.get(reverse('api-fs-children', args=[oid]))
    #    self.assertEqual(response.status_code, 200)

    def test_api_fs_organization(self):
        oid = 'ddr-densho'
        response = self.client.get(reverse('api-fs-detail', args=[oid]))
        self.assertEqual(response.status_code, 200)

    #def test_api_fs_organization_children(self):
    #    oid = 'ddr-densho'
    #    response = self.client.get(reverse('api-fs-children', args=[oid]))
    #    self.assertEqual(response.status_code, 200)

    def test_api_fs_collection(self):
        oid = 'ddr-densho-10'
        response = self.client.get(reverse('api-fs-detail', args=[oid]))
        self.assertEqual(response.status_code, 200)

    #def test_api_fs_collection_children(self):
    #    oid = 'ddr-densho-10'
    #    response = self.client.get(reverse('api-fs-children', args=[oid]))
    #    self.assertEqual(response.status_code, 200)

    def test_api_fs_entity(self):
        oid = 'ddr-densho-10-1'
        response = self.client.get(reverse('api-fs-detail', args=[oid]))
        self.assertEqual(response.status_code, 200)

    #def test_api_fs_entity_children(self):
    #    oid = 'ddr-densho-10-1'
    #    response = self.client.get(reverse('api-fs-children', args=[oid]))
    #    self.assertEqual(response.status_code, 200)

    def test_api_fs_file(self):
        oid = 'ddr-densho-10-1-mezzanine-c85f8d0f91'
        response = self.client.get(reverse('api-fs-detail', args=[oid]))
        self.assertEqual(response.status_code, 200)


class APISearchView(TestCase):

    def test_search_index(self):
        response = self.client.get(reverse('api-search'))
        self.assertEqual(response.status_code, 200)
    
    @pytest.mark.skipif(no_elasticsearch(), reason=NO_ELASTICSEARCH_ERR)
    def test_search_results(self):
        url = reverse('api-search') + '?fulltext=seattle'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    @pytest.mark.skipif(no_elasticsearch(), reason=NO_ELASTICSEARCH_ERR)
    def test_search_results_pagination(self):
        url = reverse('api-search') + '?fulltext=seattle&offset=25'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    @pytest.mark.skipif(no_elasticsearch(), reason=NO_ELASTICSEARCH_ERR)
    def test_search_results_filter(self):
        url = reverse('api-search') + '?fulltext=seattle&genre=photograph'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
