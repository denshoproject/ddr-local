from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils import unittest
from django.test.client import Client


USERNAME = settings.TESTING_USERNAME
LABEL = settings.TESTING_DRIVE_LABEL


#reverse('webui-collection', args=[repo,org,cid])
#    url(r'^remount/0/$', 'storage.views.remount0', name='storage-remount0'),
#    url(r'^remount/1/$', 'storage.views.remount1', name='storage-remount1'),
#    url(r'^storage-required/$', 'storage.views.storage_required', name='storage-required'),
#    url(r'^$', 'storage.views.index', name='storage-index'),

class StorageTest(unittest.TestCase):
    urls = 'storage.urls'
    
    def setUp(self):
        self.client = Client()
    
    def test_00_zero_out(self):
        """Unmount anything that is mounted.
        
        [{'uuid': '408A51BE8A51B160', 'mountpaths': '/media/WD5000BMV-2',
          'isreadonly': '0', 'ismounted': '1', 'label': 'WD5000BMV-2',
          'type': 'ntfs', 'devicefile': '/dev/sdb1'}]
        [{'mountpath': '/media/WD5000BMV-2', 'devicefile': '/dev/sdb1'}]
        
        <form name="mount" action="" method="post">
          <input checked="checked" name="device" type="radio" value="/media/WD5000BMV-2 /dev/sdb1" />
          <input name="which" type="hidden" value="umount" />
          <input name="submit" type="submit" value="Unmount selected device" />
        </form>
        """
        url = reverse('storage-index')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # unmount anything that's currently mounted
        mounted = response.context['removables_mounted']
        if mounted:
            for m in mounted:
                device = ' '.join([m['mountpath'], m['devicefile']])
                response1 = self.client.post(url, {'device':device, 'which':'umount'}, follow=True)
                self.assertEqual(response1.status_code, 200)
                mounted = response1.context['removables_mounted']
        # now we should have a blank slate
        self.assertEqual(mounted, [])
    
    def test_01_index(self):
        url = reverse('storage-index')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_02_mount(self):
        """Mount the device specified in ddr.cfg testing.drive_label
        
        response0.context['removables']
            [{'uuid': '408A51BE8A51B160', 'isreadonly': '0', 'ismounted': '0',
              'label': 'WD5000BMV-2', 'type': 'ntfs', 'devicefile': '/dev/sdb1'}]
        """
        # visit storage-index, get list of mounted
        url = reverse('storage-index')
        response0 = self.client.get(url)
        self.assertEqual(response0.status_code, 200)
        # nothing should be mounted at this point
        mounted = [m['mountpath'] for m in response0.context['removables_mounted']]
        self.assertEqual(mounted, [])
        # assemble a device label
        device = None
        for r in response0.context['removables']:
            if r['label'] == LABEL:
                device = ' '.join([ r['devicefile'], r['label'] ])
        self.assertTrue(device != None)
        # mount device
        response1 = self.client.post(url, {'device':device, 'which':'mount'}, follow=True)
        self.assertEqual(response1.status_code, 200)
        mounted = response1.context['removables_mounted']
        self.assertTrue(mounted != [])
