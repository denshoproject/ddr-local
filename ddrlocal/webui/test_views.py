from datetime import datetime

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client


USERNAME = settings.TESTING_USERNAME
PASSWORD = settings.TESTING_PASSWORD
REPO     = settings.TESTING_REPO
ORG      = settings.TESTING_ORG
CID      = settings.TESTING_CID
EID      = settings.TESTING_EID
ROLE     = settings.TESTING_ROLE
SHA1     = settings.TESTING_SHA1
CREATE   = settings.TESTING_CREATE
GIT_USER = settings.DDR_PROTOTYPE_USER
GIT_MAIL = settings.DDR_PROTOTYPE_MAIL


#reverse('webui-collection', args=[repo,org,cid])

class Webui00Test(TestCase):
    #urls = 'webui.urls'
    
    def setUp(self):
        self.client = Client()
    
    def test_00_index(self):
        url = reverse('webui-index')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_01_login(self):
        url = reverse('webui-login')
        response0 = self.client.get(url)
        self.assertEqual(response0.status_code, 200)
        response1 = self.client.post(url, {'username':USERNAME, 'password':PASSWORD}, follow=True)
        self.assertEqual(response1.status_code, 200)
        self.assertContains(response1, USERNAME)
        self.assertContains(response1, 'logout')
        self.assertNotContains(response1, 'login')
    
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



class Webui01CollectionTest(TestCase):
    #urls = 'webui.urls'
    
    def setUp(self):
        self.client = Client()
    
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

#webui-collection-entities



class Webui01CollectionEditTest(TestCase):
    
    def setUp(self):
        self.client = Client()
        url = reverse('webui-login')
        response = self.client.get(url)
        response = self.client.post(url, {'username':USERNAME, 'password':PASSWORD}, follow=True)
    
    def test_03_collection_edit(self):
        """Edit collection, confirm that edited text appears there.
        
        Simulate login*.
        Create a test string.
        Load form.  Check that we're logged in, get form data.
        Use form data to populate fields for a POST.
        Put test string in "notes" field.
        After POST, check webui-collection for presence of test string.
        
        * Login simulated by adding 'git_name' and 'git_mail' to session.
        
        seealso: test_03_entity_edit
        """
        session = self.client.session
        session['git_name'] = GIT_USER
        session['git_mail'] = GIT_MAIL
        session.save()
        # The test string
        test_string = datetime.now().strftime('tested on %Y-%m-%d at %H:%M:%S')
        # GET
        url = reverse('webui-collection-edit', args=[REPO, ORG, CID])
        response0 = self.client.get(url, follow=True)
        self.assertTrue(response0.status_code in [200,302])
        self.assertNotContains(response0, 'login')  # make sure we're "logged in"
        self.assertContains(response0, 'logout')
        form = response0.context['form']            # get form data from context
        form.data['notes'] = test_string            # change value of "notes"
        # POST
        response1 = self.client.post(url, form.data, follow=True)
        self.assertEqual(response1.status_code, 200)
        for line in response1.content.split('\n'):
            if (line.find('"errorlist"') > -1):
                print('COLLECTION FORM: %s' % line)
        # GET
        url2 = reverse('webui-collection', args=[REPO, ORG, CID])
        response2 = self.client.get(url2, follow=True)
        self.assertEqual(response2.status_code, 200)
        self.assertContains(response2, test_string) # test string is present?

#webui-collection-new
#webui-collection-sync



class Webui02EntityTest(TestCase):
    #urls = 'webui.urls'
    
    def setUp(self):
        self.client = Client()
    
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



class Webui02EntityEditTest(TestCase):
    
    def setUp(self):
        self.client = Client()
        url = reverse('webui-login')
        response = self.client.get(url)
        response = self.client.post(url, {'username':USERNAME, 'password':PASSWORD}, follow=True)
    
    def test_03_entity_edit(self):
        """Edit collection, confirm that edited text appears there.
        
        Simulate login*.
        Create a test string.
        Load form.  Check that we're logged in, get form data.
        Use form data to populate fields for a POST.
        Put test string in "notes" field.
        After POST, check webui-collection for presence of test string.
        
        * Login simulated by adding 'git_name' and 'git_mail' to session.
        
        seealso: test_03_collection_edit
        """
        session = self.client.session  # simulate login
        session['git_name'] = GIT_USER
        session['git_mail'] = GIT_MAIL
        session.save()
        # The test string
        test_string = datetime.now().strftime('tested on %Y-%m-%d at %H:%M:%S')
        # GET
        url = reverse('webui-entity-edit', args=[REPO, ORG, CID, EID])
        response0 = self.client.get(url, follow=True)
        self.assertTrue(response0.status_code in [200,302])
        self.assertNotContains(response0, 'login')  # make sure we're "logged in"
        self.assertContains(response0, 'logout')
        form = response0.context['form']            # get form data from context
        form.data['notes'] = test_string            # change value of "notes"
        # POST
        response1 = self.client.post(url, form.data, follow=True)
        self.assertEqual(response1.status_code, 200)
        for line in response1.content.split('\n'):
            if (line.find('"errorlist"') > -1):
                print('ENTITY FORM: %s' % line)
        # get
        url2 = reverse('webui-entity', args=[REPO, ORG, CID, EID])
        response2 = self.client.get(url2, follow=True)
        self.assertEqual(response2.status_code, 200)
        self.assertContains(response2, test_string) # test string is present?

#webui-entity-new
#webui-entity-edit-json
#webui-entity-edit-mets-xml
#webui-entity-edit-mets



class Webui03FileTest(TestCase):
    #urls = 'webui.urls'
    
    def setUp(self):
        self.client = Client()
    
    def test_02_file(self):
        url = reverse('webui-file', args=[REPO, ORG, CID, EID, ROLE, SHA1])
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
    
    def test_02_file_json(self):
        url = reverse('webui-file-json', args=[REPO, ORG, CID, EID, ROLE, SHA1])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
    
    def test_02_file_edit(self):
        url = reverse('webui-file-edit', args=[REPO, ORG, CID, EID, ROLE, SHA1])
        response0 = self.client.get(url, follow=True)
        self.assertTrue(response0.status_code in [200,302])
        response1 = self.client.post(url, {}, follow=True)
        self.assertEqual(response1.status_code, 200)

#webui-file-edit
#webui-file-new-access
# 
#webui-file-batch-master
#webui-file-batch-mezzanine
#webui-file-new-master
#webui-file-new-mezzanine
#webui-file-new
