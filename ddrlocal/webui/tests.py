from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils import unittest
from django.test.client import Client


username = settings.TESTING_USERNAME
password = settings.TESTING_PASSWORD

#reverse('webui-collection', args=[repo,org,cid])

class WebuiTest(unittest.TestCase):
    urls = 'webui.urls'
    
    def setUp(self):
        # Every test needs a client.
        self.client = Client()
    
    def test_00_index(self):
        url = reverse('webui-index')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_01_login(self):
        url = reverse('webui-login')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(url, {'username':username, 'password':password}, follow=True)
        self.assertEqual(response.status_code, 200)
    
    def test_02_tasks(self):
        url = reverse('webui-tasks')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_02_task_status(self):
        url = reverse('webui-task-status')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)



class WebuiCollectionTest(unittest.TestCase):
    urls = 'webui.urls'
    repo = 'ddr'
    org = 'testing'
    cid = 120
    
    def setUp(self):
        self.client = Client()
    
    def test_00_login(self):
        url = reverse('webui-login')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(url, {'username':username, 'password':password}, follow=True)
        self.assertEqual(response.status_code, 200)
    
    def test_99_logout(self):
        url = reverse('webui-logout')
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('Logged out' in response.content)
    
    def test_01_collections(self):
        url = reverse('webui-collections')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        repo = response.context['collections'][0][1]
        org = response.context['collections'][0][2]
        collections = response.context['collections'][0][3]
        collections.sort()
        self.repo = repo
        self.org = org
        self.assertTrue(self.repo != None)
        self.assertTrue(self.org != None)
        self.assertTrue(collections != None)
        print('test_01_collections')
        print('self.repo: %s' % self.repo)
        print('self.org: %s' % self.org)
    
    def test_02_collection(self):
        url = reverse('webui-collection', args=[self.repo, self.org, self.cid])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        print('test_02_collection')
        print('self.repo: %s' % self.repo)
        print('self.org: %s' % self.org)
    
    def test_02_collection_json(self):
        url = reverse('webui-collection-json', args=[self.repo, self.org, self.cid])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
    
    def test_02_collection_changelog(self):
        url = reverse('webui-collection-changelog', args=[self.repo, self.org, self.cid])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_02_collection_gitstatus(self):
        url = reverse('webui-collection-git-status', args=[self.repo, self.org, self.cid])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_02_collection_xml(self):
        url = reverse('webui-collection-ead-xml', args=[self.repo, self.org, self.cid])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/xml')

#webui-collection-entities
#webui-collection-new
#webui-collection-edit
#webui-collection-sync


class WebuiEntityTest(unittest.TestCase):
    urls = 'webui.urls'
    repo = 'ddr'
    org = 'testing'
    cid = 120
    eid = 1
    
    def setUp(self):
        self.client = Client()
    
    def test_00_login(self):
        url = reverse('webui-login')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(url, {'username':username, 'password':password}, follow=True)
        self.assertEqual(response.status_code, 200)
    
    def test_99_logout(self):
        url = reverse('webui-logout')
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('Logged out' in response.content)
    
    def test_02_entity(self):
        url = reverse('webui-entity', args=[self.repo, self.org, self.cid, self.eid])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_02_entity_json(self):
        url = reverse('webui-entity-json', args=[self.repo, self.org, self.cid, self.eid])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
    
    def test_02_entity_changelog(self):
        url = reverse('webui-entity-changelog', args=[self.repo, self.org, self.cid, self.eid])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_02_entity_addfilelog(self):
        url = reverse('webui-entity-addfilelog', args=[self.repo, self.org, self.cid, self.eid])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_02_entity_xml(self):
        url = reverse('webui-entity-mets-xml', args=[self.repo, self.org, self.cid, self.eid])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

#webui-entity-new
#webui-entity-edit-json
#webui-entity-edit-mets-xml
#webui-entity-edit-mets
#webui-entity-edit


class WebuiFileTest(unittest.TestCase):
    urls = 'webui.urls'
    repo = 'ddr'
    org = 'testing'
    cid = 120
    eid = 1
    role = 'master'
    sha1 = 'dd9ec4305d'
    
    def setUp(self):
        self.client = Client()
    
    def test_00_login(self):
        url = reverse('webui-login')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(url, {'username':username, 'password':password}, follow=True)
        self.assertEqual(response.status_code, 200)
    
    def test_99_logout(self):
        url = reverse('webui-logout')
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('Logged out' in response.content)
    
    def test_02_file(self):
        url = reverse('webui-file', args=[self.repo, self.org, self.cid, self.eid, self.role, self.sha1])
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
    
    def test_02_file_json(self):
        url = reverse('webui-file-json', args=[self.repo, self.org, self.cid, self.eid, self.role, self.sha1])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

#webui-file-edit
#webui-file-new-access
# 
#webui-file-batch-master
#webui-file-batch-mezzanine
#webui-file-new-master
#webui-file-new-mezzanine
#webui-file-new
# 
#webui-index
