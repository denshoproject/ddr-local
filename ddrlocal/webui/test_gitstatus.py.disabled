from datetime import datetime, timedelta
import os
import shutil

from django.test import TestCase

from webui import gitstatus


BASEDIR = '/tmp/test-gitstatus'

SYNCSTATUS = '{"status": "synced", "timestamp": "1969-12-31T16:00:00:000000"}'

DUMPS = '''1969-12-31T16:00:00:000000 0:00:01.234567
%%
STATUS
%%
ANNEX
%%
{"status": "synced", "timestamp": "1969-12-31T16:00:00:000000"}'''

LOADS = {
    'timestamp': datetime.fromtimestamp(0),
    'elapsed': '0:00:01.234567',
    'status': 'STATUS',
    'annex_status': 'ANNEX',
    'sync_status': '{"status": "synced", "timestamp": "1969-12-31T16:00:00:000000"}'
}

COLLECTIONS = [
    'ddr-test-123',
    'ddr-test-124',
    'ddr-test-136',
    'ddr-test-248',
]

class GitstatusTests(TestCase):
    
    def setUp(self):
        if os.path.exists(BASEDIR):
            shutil.rmtree(BASEDIR)
    
    # log
     
    def test_tmp_dir(self):
        out = gitstatus.tmp_dir(BASEDIR)
        expected = os.path.join(BASEDIR, 'tmp')
        self.assertEqual(expected, out)
     
    def test_queue_path(self):
        out = gitstatus.queue_path(BASEDIR)
        expected = os.path.join(BASEDIR, 'tmp', 'gitstatus-queue')
        self.assertEqual(expected, out)
     
    def test_lock_path(self):
        out = gitstatus.lock_path(BASEDIR)
        expected = os.path.join(BASEDIR, 'tmp', 'gitstatus-lock')
        self.assertEqual(expected, out)
     
    def test_path(self):
        out = gitstatus.path(BASEDIR, '/media/LABEL/ddr/ddr-test-123')
        expected = os.path.join(BASEDIR, 'tmp', 'ddr-test-123.status')
        self.assertEqual(expected, out)

    def test_status_paths(self):
        expected = []
        tmp_dir = os.path.join(BASEDIR, 'tmp')
        os.makedirs(tmp_dir)
        for cid in COLLECTIONS[1:]:
            path = os.path.join(tmp_dir, '%s.status' % cid)
            expected.append(path)
            with open(path, 'w') as f:
                f.write('nothing here')
        out = gitstatus.status_paths(BASEDIR)
        self.assertEqual(expected, out)

#    def test_dumps(self):
#        out = gitstatus.dumps(
#            datetime.fromtimestamp(0),
#            timedelta(seconds=1.234567),
#            'STATUS',
#            'ANNEX',
#            SYNCSTATUS
#        )
#        self.assertEqual(DUMPS, out)
     
#    def test_loads(self):
#        out = gitstatus.loads(DUMPS)
#        self.assertEqual(out, LOADS, GITSTATU)
     
#    def test_write(self):
#        pass
#     
#    def test_read(self):
#        pass
#     
#    def test_sync_status(self):
#        pass
#     
#    def test_update(self):
#        pass

    def test_lock(self):
        os.makedirs(os.path.join(BASEDIR, 'tmp'))
        lock_path = os.path.join(BASEDIR, 'tmp', 'gitstatus-lock')
        
        # no lockfile
        lockfile_before = os.path.exists(lock_path)
        before = os.path.exists(lock_path)
        self.assertEqual(before, False)
        self.assertEqual(lockfile_before, False)
        
        tids = ['1234', '1248']
        
        # '2014-07-15T15:17:15:254884 1234'
        lockfile_after = gitstatus.lock(BASEDIR, tids[0])
        after = os.path.exists(lock_path)
        self.assertEqual(after, True)
        self.assertIsNotNone(lockfile_after)
        # check if properly formed
        ts1,msg1 = lockfile_after.strip().split()
        timestamp1 = datetime.strptime(ts1, '%Y-%m-%dT%H:%M:%S:%f')
        self.assertEqual(isinstance(timestamp1, datetime), True)
        self.assertEqual(msg1, tids[0])
        
        # '2014-07-15T15:17:15:254884 1234\n2014-07-15T15:17:15:254907 1248'
        lockfile_again = gitstatus.lock(BASEDIR, tids[1])
        again = os.path.exists(lock_path)
        self.assertEqual(again, True)
        self.assertIsNotNone(lockfile_again)
        # check if properly formed
        lines = lockfile_again.strip().split('\n')
        self.assertEqual(len(lines), 2)
        for n,line in enumerate(lines):
            ts2,msg2 = line.strip().split()
            timestamp2 = datetime.strptime(ts2, '%Y-%m-%dT%H:%M:%S:%f')
            self.assertEqual(isinstance(timestamp2, datetime), True)
            self.assertEqual(msg2, tids[n])

    def test_unlock(self):
        os.makedirs(os.path.join(BASEDIR, 'tmp'))
        lock_path = os.path.join(BASEDIR, 'tmp', 'gitstatus-lock')
        
        before = os.path.exists(lock_path)
        self.assertEqual(before, False)
        
        # lock twice
        tids = ['1234', '1248']
        lockfile0 = gitstatus.lock(BASEDIR, tids[0])
        after0 = os.path.exists(lock_path)
        lockfile1 = gitstatus.lock(BASEDIR, tids[1])
        after1 = os.path.exists(lock_path)
        self.assertEqual(after0, True)
        self.assertEqual(after1, True)
        self.assertEqual(len(lockfile1.strip().split('\n')), 2)
        
        # unlock
        unlocked0 = gitstatus.unlock(BASEDIR, tids[0])
        unlocked1 = gitstatus.unlock(BASEDIR, tids[1])
        self.assertEqual(len(unlocked0.strip().split('\n')), 1)
        self.assertEqual(unlocked1, '')

    def test_locked_global(self):
        os.makedirs(os.path.join(BASEDIR, 'tmp'))
        lock_path = os.path.join(BASEDIR, 'tmp', 'gitstatus-lock')
        self.assertEqual(gitstatus.locked_global(BASEDIR), False)
        # lock
        tids = ['1234', '1248']
        lockfile0 = gitstatus.lock(BASEDIR, tids[0])
        self.assertNotEqual(gitstatus.locked_global(BASEDIR), False)
        lockfile1 = gitstatus.lock(BASEDIR, tids[1])
        self.assertNotEqual(gitstatus.locked_global(BASEDIR), False)
        # unlock
        unlocked0 = gitstatus.unlock(BASEDIR, tids[0])
        self.assertNotEqual(gitstatus.locked_global(BASEDIR), False)
        unlocked1 = gitstatus.unlock(BASEDIR, tids[1])
        self.assertEqual(gitstatus.locked_global(BASEDIR), False)

#    def test_queue_loads(self):
#        pass
#     
#    def test_queue_dumps(self):
#        pass
#     
#    def test_queue_read(self):
#        pass
#     
#    def test_queue_write(self):
#        pass
#     
#    def test_queue_generate(self):
#        pass
#     
#    def test_queue_mark_updated(self):
#        pass

    def test_next_time(self):
        out = gitstatus.next_time(10, 1)
        self.assertEqual(isinstance(out, datetime), True)
        # TODO needs moar test

    def test_its_ready(self):
        epoch = datetime.fromtimestamp(0)
        future = datetime(3000,1,1)
        self.assertEqual(gitstatus.its_ready(epoch, 0), True)
        self.assertEqual(gitstatus.its_ready(future, 0), False)

#    def test_next_repo(self):
#        pass
#     
#    def test_update_store(self):
#        pass
