"""
Loading Test Data

ddrindex destroy --confirm
ddrindex create
ddrindex vocabs /opt/densho-vocab/api/0.2/
ddrindex narrators /opt/densho-vocab/api/0.2/narrators.json
ddrindex repo /var/www/media/ddr/ddr/repository.json
ddrindex org /var/www/media/ddr/ddr-densho/organization.json
ddrindex publish -r --force /var/www/media/ddr/ddr-densho-10
ddrindex publish -r --force /var/www/media/ddr/ddr-csujad-30
"""

import pytest
import requests

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from elastictools.docstore import DocstoreManager, TransportError
from webui.models import INDEX_PREFIX

HOST_CHECK_URL = 'http://{}'.format(settings.DOCSTORE_HOST)

NO_ELASTICSEARCH_ERR = "Elasticsearch cluster not available."
def no_elasticsearch():
    """Returns True if cannot contact cluster; use to skip tests
    """
    try:
        DocstoreManager(INDEX_PREFIX, settings.DOCSTORE_HOST, settings).start_test()
    except ConnectionError:
        print('ConnectionError')
        return True
    except TransportError:
        print('TransportError')
        return True
    return True


class AuthView(TestCase):
    pass
    # webui-login
    # webui-logout


class TaskView(TestCase):

    def test_tasks(self):
        response = self.client.get(reverse('webui-tasks'))
        self.assertEqual(response.status_code, 200)

    def test_task_status(self):
        response = self.client.get(reverse('webui-task-status'))
        self.assertEqual(response.status_code, 200)
    
    # webui-tasks-dismiss


class IndexView(TestCase):

    def test_index(self):
        response = self.client.get(reverse('webui-index'))
        self.assertEqual(response.status_code, 200)

    #def test_collections(self):
    #    response = self.client.get(reverse('webui-collections'))
    #    self.assertEqual(response.status_code, 200)


# webui-repository
# webui-organization


class CollectionView(TestCase):

    def test_00_detail(self):
        oid = 'ddr-densho-10'
        response = self.client.get(reverse('webui-collection', args=[oid]))
        self.assertEqual(response.status_code, 200)

    def test_01_changelog(self):
        oid = 'ddr-densho-10'
        response = self.client.get(
            reverse('webui-collection-changelog', args=[oid])
        )
        self.assertEqual(response.status_code, 200)

    def test_01_gitstatus(self):
        oid = 'ddr-densho-10'
        response = self.client.get(
            reverse('webui-collection-git-status', args=[oid])
        )
        self.assertEqual(response.status_code, 200)

    def test_90_children(self):
        oid = 'ddr-densho-10'
        response = self.client.get(
            reverse('webui-collection-children', args=[oid])
        )
        self.assertEqual(response.status_code, 200)

    # webui-collection-sync-status-ajax
    # webui-collection-export-entities
    # webui-collection-export-files
    # webui-collection-csv-entities
    # webui-collection-csv-files
    # webui-collection-import-entities
    # webui-collection-import-files
    # webui-collection-newidservice
    # webui-collection-newmanual
    # webui-collection-new
    # webui-collection-edit
    # webui-collection-sync
    # webui-collection-check
    # webui-collection-signatures
    # webui-collection-unlock


class EntityView(TestCase):

    def test_detail(self):
        oid = 'ddr-densho-10'
        response = self.client.get(reverse('webui-entity', args=[oid]))
        self.assertEqual(response.status_code, 200)

    def test_detail(self):
        oid = 'ddr-densho-10-1'
        response = self.client.get(reverse('webui-entity', args=[oid]))
        self.assertEqual(response.status_code, 200)

    def test_detail(self):
        oid = 'ddr-densho-10-1'
        response = self.client.get(reverse('webui-segment', args=[oid]))
        self.assertEqual(response.status_code, 200)

    def test_changelog(self):
        oid = 'ddr-densho-10-1'
        response = self.client.get(reverse('webui-entity-changelog', args=[oid]))
        self.assertEqual(response.status_code, 200)

    def test_addfilelog(self):
        oid = 'ddr-densho-10-1'
        response = self.client.get(reverse('webui-entity-addfilelog', args=[oid]))
        self.assertEqual(response.status_code, 200)

    def test_children(self):
        oid = 'ddr-densho-10-1'
        response = self.client.get(
            reverse('webui-entity-children', args=[oid])
        )
        self.assertEqual(response.status_code, 200)

    # webui-entity-newidservice
    # webui-entity-newmanual
    # webui-entity-new
    # webui-entity-edit
    # webui-entity-unlock
    # webui-entity-delete
    # webui-entity-files-reload
    # webui-entity-files-dedupe


class FileView(TestCase):

    def test_role(self):
        oid = 'ddr-densho-10-1-mezzanine'
        response = self.client.get(reverse('webui-file-role', args=[oid]))
        self.assertEqual(response.status_code, 200)

    def test_detail(self):
        oid = 'ddr-densho-10-1-mezzanine-c85f8d0f91'
        response = self.client.get(reverse('webui-file', args=[oid]))
        self.assertEqual(response.status_code, 200)

    # webui-file-new-master
    # webui-file-new-mezzanine
    # webui-file-new
    # webui-file-new-external
    # webui-file-new-access
    # webui-file-sig
    # webui-file-edit
    # webui-file-delete
    # webui-file-batch
    # webui-file-browse


class VocabsView(TestCase):

    def test_vocab_terms(self):
        response = self.client.get(
            reverse('webui-entity-vocab-terms', args=['topics'])
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse('webui-entity-vocab-terms', args=['facility'])
        )
        self.assertEqual(response.status_code, 200)


# Check the search_form in response context.
# Look for certain topics filter choices, ignoring counts
# NOTE: The actual topics labels are long, so look for fragments
def find_filter_choice(response, field, choice_key, label_fragment):
    choices = response.context['search_form'].fields[field].choices
    for key,label in choices:
        if (key == choice_key) and (label_fragment in label):
            return True
    return False

def find_filter_choices(response, field_choices):
    for field,term_id,label in field_choices:
        assert find_filter_choice(response, 'topics', term_id, label)

SEARCH_FILTER_CHOICES = [
    ('topics', '167', 'Legal cases/coram nobis cases'),
    ('topics', '97', 'Supreme Court cases -- Gordon Hirabayashi'),
]

CREATORS_SEARCH_FILTER_CHOICES = [
    ('topics', '195', 'World War II -- Concentration camps -- Social and recreational activities'),
    ('topics', '67', 'World War II -- Concentration camps -- Living conditions'),
    ('topics', '484', 'Geographic communities -- California -- Livingston'),
]

class SearchView(TestCase):
 
    def test_search_index(self):
        response = self.client.get(reverse('webui-search'))
        self.assertEqual(response.status_code, 200)
    
    @pytest.mark.skipif(no_elasticsearch(), reason=NO_ELASTICSEARCH_ERR)
    def test_search_results(self):
        url = reverse(
            'webui-search'
        ) + '?fulltext=seattle'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        find_filter_choices(response, SEARCH_FILTER_CHOICES)
    
    @pytest.mark.skipif(no_elasticsearch(), reason=NO_ELASTICSEARCH_ERR)
    def test_search_results_pagination(self):
        url = reverse(
            'webui-search'
        ) + '?fulltext=seattle&page=2'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        find_filter_choices(response, SEARCH_FILTER_CHOICES)
    
    @pytest.mark.skipif(no_elasticsearch(), reason=NO_ELASTICSEARCH_ERR)
    def test_search_results_filter(self):
        url = reverse(
            'webui-search'
        ) + '?fulltext=seattle&genre=photograph'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        find_filter_choices(response, SEARCH_FILTER_CHOICES)
 
    def test_collection_search_index(self):
        url = reverse('webui-collection-search', args=['ddr-densho-10'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    @pytest.mark.skipif(no_elasticsearch(), reason=NO_ELASTICSEARCH_ERR)
    def test_collection_search_results(self):
        url = reverse(
            'webui-collection-search',
            args=['ddr-densho-10'],
        ) + '?fulltext=seattle'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        find_filter_choices(response, SEARCH_FILTER_CHOICES)
    
    @pytest.mark.skipif(no_elasticsearch(), reason=NO_ELASTICSEARCH_ERR)
    def test_collection_search_results_pagination(self):
        url = reverse(
            'webui-collection-search',
            args=['ddr-densho-10'],
        ) + '?fulltext=seattle&page=2'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        find_filter_choices(response, SEARCH_FILTER_CHOICES)

    @pytest.mark.skipif(no_elasticsearch(), reason=NO_ELASTICSEARCH_ERR)
    def test_search_results_creators(self):
        url = reverse(
            'webui-search'
        ) + '?fulltext=Katabami,%20Reiko'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        find_filter_choices(response, CREATORS_SEARCH_FILTER_CHOICES)

    @pytest.mark.skipif(no_elasticsearch(), reason=NO_ELASTICSEARCH_ERR)
    def test_search_results_creators_filters(self):
        url = reverse(
            'webui-search'
        ) + '?fulltext=Katabami,%20Reiko&topics=484'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        find_filter_choices(response, CREATORS_SEARCH_FILTER_CHOICES)

    @pytest.mark.skipif(no_elasticsearch(), reason=NO_ELASTICSEARCH_ERR)
    def test_search_results_persons(self):
        url = reverse(
            'webui-search'
        ) + '?fulltext=Yasui,%20Sachi'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

class TaskView(TestCase):

    def test_tasks(self):
        response = self.client.get(reverse('webui-tasks'))
        self.assertEqual(response.status_code, 200)

    def test_task_status(self):
        response = self.client.get(reverse('webui-task-status'))
        self.assertEqual(response.status_code, 200)
    
    # webui-tasks-dismiss


# webui-gitstatus-queue
# webui-gitstatus-toggle
# webui-restart
# webui-supervisord-procinfo-html
# webui-supervisord-procinfo-json
# webui-supervisord-restart
# webui-merge-auto
# webui-merge-json
# webui-merge-raw
# webui-merge
