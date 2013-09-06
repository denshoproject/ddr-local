from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils import unittest
from django.test.client import Client


USERNAME = settings.TESTING_USERNAME
PASSWORD = settings.TESTING_PASSWORD
REPO     = settings.TESTING_REPO
ORG      = settings.TESTING_ORG
CID      = settings.TESTING_CID
EID      = settings.TESTING_EID
ROLE     = settings.TESTING_ROLE
SHA1     = settings.TESTING_SHA1


#reverse('webui-collection', args=[repo,org,cid])

class Webui00Test(unittest.TestCase):
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
        response = self.client.post(url, {'username':USERNAME, 'password':PASSWORD}, follow=True)
        self.assertEqual(response.status_code, 200)
    
    def test_02_tasks(self):
        url = reverse('webui-tasks')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_02_task_status(self):
        url = reverse('webui-task-status')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_99_logout(self):
        url = reverse('webui-logout')
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('Logged out' in response.content)



class Webui01CollectionTest(unittest.TestCase):
    urls = 'webui.urls'
    
    def setUp(self):
        self.client = Client()
    
    def test_00_login(self):
        url = reverse('webui-login')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(url, {'username':USERNAME, 'password':PASSWORD}, follow=True)
        self.assertEqual(response.status_code, 200)
    
    def test_01_collections(self):
        url = reverse('webui-collections')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        repo = response.context['collections'][0][1]
        org = response.context['collections'][0][2]
        collections = response.context['collections'][0][3]
        collections.sort()
        self.assertTrue(repo != None)
        self.assertTrue(org != None)
        self.assertTrue(collections != None)
    
    def test_02_collection(self):
        url = reverse('webui-collection', args=[REPO, ORG, CID])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_02_collection_json(self):
        url = reverse('webui-collection-json', args=[REPO, ORG, CID])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
    
    def test_02_collection_changelog(self):
        url = reverse('webui-collection-changelog', args=[REPO, ORG, CID])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_02_collection_gitstatus(self):
        url = reverse('webui-collection-git-status', args=[REPO, ORG, CID])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_02_collection_xml(self):
        url = reverse('webui-collection-ead-xml', args=[REPO, ORG, CID])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/xml')
    
    def test_99_logout(self):
        url = reverse('webui-logout')
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('Logged out' in response.content)

#webui-collection-entities
#webui-collection-new
#webui-collection-edit
#webui-collection-sync


class Webui02EntityTest(unittest.TestCase):
    urls = 'webui.urls'
    
    def setUp(self):
        self.client = Client()
    
    def test_00_login(self):
        url = reverse('webui-login')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(url, {'username':USERNAME, 'password':PASSWORD}, follow=True)
        self.assertEqual(response.status_code, 200)
    
    def test_02_entity(self):
        url = reverse('webui-entity', args=[REPO, ORG, CID, EID])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_02_entity_json(self):
        url = reverse('webui-entity-json', args=[REPO, ORG, CID, EID])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
    
    def test_02_entity_changelog(self):
        url = reverse('webui-entity-changelog', args=[REPO, ORG, CID, EID])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_02_entity_addfilelog(self):
        url = reverse('webui-entity-addfilelog', args=[REPO, ORG, CID, EID])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_02_entity_xml(self):
        url = reverse('webui-entity-mets-xml', args=[REPO, ORG, CID, EID])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_99_logout(self):
        url = reverse('webui-logout')
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('Logged out' in response.content)

#webui-entity-new
#webui-entity-edit-json
#webui-entity-edit-mets-xml
#webui-entity-edit-mets
#webui-entity-edit


class Webui03FileTest(unittest.TestCase):
    urls = 'webui.urls'
    
    def setUp(self):
        self.client = Client()
    
    def test_01_login(self):
        url = reverse('webui-login')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(url, {'username':USERNAME, 'password':PASSWORD}, follow=True)
        self.assertEqual(response.status_code, 200)
    
    def test_02_file(self):
        url = reverse('webui-file', args=[REPO, ORG, CID, EID, ROLE, SHA1])
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
    
    def test_02_file_json(self):
        url = reverse('webui-file-json', args=[REPO, ORG, CID, EID, ROLE, SHA1])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
    
    def test_99_logout(self):
        url = reverse('webui-logout')
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('Logged out' in response.content)

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
