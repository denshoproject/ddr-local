"""
gitstatus

This module was born out of a desire to show users the status of
repositories in relation to the central server, and several attempts
to improve performance that resulted.

Once there are enough large collections in a Store running git-status
and git-annex-status starts to take a long time.
Previous attempts to address this involved caching the status,
and running the git-status updates after page-load in response
to AJAX requests.  Neither of these approaches worked well.

With this module, git-status and git-annex-status are run in the
background by Celery/celerybeat.  The background process uses a queue
file that resides at the root of the Store that is currently in use
(new queue file is created as needed).  The results for individual
collection repositories are written to files at the root of the repos.
The UI gets status info from these files rather than running
git-status/git-annex-status directly.  Cache files hang around until
they are replaced.  The user is informed when the files were last
updated and (TODO) can request an update if they want.


Queue file

List of collection_ids and timestamps, arranged in timestamp order (ASCENDING)
Collections that have not been updated are timestamped with past date (epoch)
First line contains date of last queue_generate().
Timestamps represent next earliest update datetime.
After running gitstatus on collection, next update time is scheduled.
Time is slightly randomized so updates gradually spread out.
"""

from datetime import datetime, timedelta
import json
import logging
logger = logging.getLogger(__name__)
import os
import random
import re

from django.conf import settings
from django.core.cache import cache

from DDR import dvcs
from DDR.storage import is_writable
from ddrlocal.models import DDRLocalCollection as Collection
from webui import COLLECTION_STATUS_TIMEOUT
from webui import gitolite
from webui.identifier import Identifier

COLLECTION_SYNC_STATUS_CACHE_KEY = 'webui:collection:%s:sync-status'


def log(msg):
    """celery does not like writing to logs, so write to separate logfile
    """
    entry = '%s %s\n' % (datetime.now().strftime(settings.TIMESTAMP_FORMAT), msg)
    with open(settings.GITSTATUS_LOG, 'a') as f:
        f.write(entry)

def tmp_dir( base_dir ):
    """Returns path to tmp dir; creates dir under certain conditions
    
    The tmp/ directory is added only if
    - the base directory is present (i.e. a Store is mounted) and
    - tmp/ is missing from the base directory.
    """
    path = os.path.join(base_dir, 'tmp')
    if os.path.exists(base_dir) and (not os.path.exists(path)):
        os.makedirs(path)
    return path

def parse_status_path(path):
    """
    @returns: base_path,collection_id
    """
    base_path = os.path.dirname(os.path.dirname(path))
    collection_id = os.path.splitext(os.path.basename(path))[0]
    return base_path,collection_id

def queue_path( base_dir ):
    """Returns path to gitstatus-queue; makes tmpdir if absent.
    """
    return os.path.join(
        tmp_dir(base_dir),
        'gitstatus-queue'
    )
    
def lock_path( base_dir ):
    """Returns path to gitstatus-lock; makes tmpdir if absent.
    """
    return os.path.join(
        tmp_dir(base_dir),
        'gitstatus-lock'
    )


class Gitstatus:
    """State of a single collection, functions for reading/writing same.
    
    Generate new data
    >>> gs = Gitstatus(Identifier('/var/www/media/ddr/ddr-test-123'))
    >>> gs.update()

    Load from file
    >>> gs = Gitstatus(Identifier('/var/www/media/ddr/ddr-test-123'))
    >>> gs.read()
    Alternatively
    >>> gs = Gitstatus.from_status_path('/var/www/media/ddr/tmp/ddr-test-123.status')
    >>> gs.read()
    
    Print
    >>> print(gs.dumps())
    
    Write to file
    >>> gs.write()
    """
    
    identifier = None
    path = None
    timestamp = None
    elapsed = None
    git_status = ''
    annex_status = ''
    sync_status = {}
    
    def __init__(self, cidentifier):
        self.identifier = cidentifier
        self.path = os.path.join(
            tmp_dir(self.identifier.basepath),
            '%s.status' % os.path.basename(self.identifier.path_abs())
        )

    @staticmethod
    def from_status_path(path):
        base_path,collection_id = parse_status_path(path)
        cidentifier = Identifier(collection_id, base_path)
        return Gitstatus(cidentifier)
    
    def update(self):
        """Gets a bunch of status info for the collection
        
        timestamp, elapsed, git_status, annex_status, syncstatus
        """
        start = datetime.now()
        self.git_status = dvcs.repo_status(self.identifier.path_abs(), short=True)
        self.annex_status = dvcs.annex_status(self.identifier.path_abs())
        self.timestamp = datetime.now()
        self.elapsed = self.timestamp - start
        self.sync_status = self._sync_status(force=True)
    
    def _sync_status(self, cache_set=False, force=False ):
        """Cache collection repo sync status info for collections list page.
        Used in both .collections() and .sync_status_ajax().
        
        TODO do we need to cache this any more? we're writing this to REPO/.gitstatus
        
        @param cache_set: Run git-status if data is not cached
        """
        # IMPORTANT: DO NOT call collection.gitstatus() it will loop
        collection_id = self.identifier.id
        key = COLLECTION_SYNC_STATUS_CACHE_KEY % collection_id
        data = cache.get(key)
        if force or (not data and cache_set):
            status = 'unknown'
            btn = 'muted'
            # we're just getting this so we can call Collection.locked
            disposable_collection = Collection.from_identifier(self.identifier)
            # now:
            if   dvcs.ahead(self.git_status): status = 'ahead'; btn = 'warning'
            elif dvcs.behind(self.git_status): status = 'behind'; btn = 'warning'
            elif dvcs.conflicted(self.git_status): status = 'conflicted'; btn = 'danger'
            elif dvcs.synced(self.git_status): status = 'synced'; btn = 'success'
            elif disposable_collection.locked(): status = 'locked'; btn = 'warning'
            timestamp = self.timestamp.strftime(settings.TIMESTAMP_FORMAT)
            data = {
                'row': '#%s' % collection_id,
                'color': btn,
                'cell': '#%s td.status' % collection_id,
                'status': self.git_status,
                'timestamp': timestamp,
            }
            cache.set(key, data, COLLECTION_STATUS_TIMEOUT)
        return data
    
    def dumps(self):
        """Formats data as text
        
        Sample:
            {timestamp} {elapsed}
            %%
            {git_status}
            %%
            {annex status}
            %%
            {sync status}
        """
        ts_elapsed = ' '.join([
            self.timestamp.strftime(settings.TIMESTAMP_FORMAT),
            str(self.elapsed)
        ])
        return '\n%%\n'.join([
            ts_elapsed,
            self.git_status,
            self.annex_status,
            json.dumps(self.sync_status),
        ])
    
    def write(self):
        """Writes .gitstatus for the collection; see format.
        """
        text = self.dumps() + '\n'
        with open(self.path, 'w') as f:
            f.write(text)
        return text
    
    def _loads(self, text):
        """Converts status data from text to Python objects
        
        @returns: dict (keys: timestamp,elapsed,git_status,annex_status,syncstatus)
        """
        # we don't know in advance how many fields exist in .gitstatus
        # so get as many as we can
        variables = [None,None,None,None]
        for n,part in enumerate(text.split('%%')):
            variables[n] = part.strip()
        meta = variables[0]
        if meta:
            ts,elapsed = meta.split(' ')
            self.timestamp = datetime.strptime(ts, settings.TIMESTAMP_FORMAT)
            self.elapsed = elapsed
        self.git_status = variables[1]
        self.annex_status = variables[2]
        syncstatus = variables[3]
        if syncstatus: # may not be present
            syncstatus = json.loads(syncstatus)
            if syncstatus.get('timestamp',None):
                syncstatus['timestamp'] = datetime.strptime(
                    syncstatus['timestamp'], settings.TIMESTAMP_FORMAT
                )
        self.sync_status = syncstatus
    
    def read(self):
        """Reads .gitstatus for the collection and returns parsed data.
        """
        if os.path.exists(self.path):
            with open(self.path, 'r') as f:
                text = f.read()
            return self._loads(text)
        return None


class GitstatusQueue:
    """List of collections to check; functions for updating, reading, writing
    
    # Run an update
    >>> q = GitstatusQueue('/var/www/media/ddr')
    >>> messages = q.update(delta=60, minimum=3600, local=False)
    
    # Examine the queue
    >>> q = GitstatusQueue('/var/www/media/ddr')
    >>> q.queue_path
    '/var/www/media/ddr/tmp/gitstatus-queue'
    >>> q.lock_path
    '/var/www/media/ddr/tmp/gitstatus-lock'
    >>> q.generated
    datetime.datetime(2016, 1, 26, 19, 34, 25, 423691)
    >>> q.collections
    [
        [datetime.datetime(2016, 1, 26, 20, 45, 25, 646472), <webui.identifier.Identifier collection:ddr-testing-300>],
        [datetime.datetime(2016, 1, 26, 20, 46, 25, 646472), <webui.identifier.Identifier collection:ddr-testing-304>],
        ...
    ]
    """
    base_dir = None
    lock_path = None
    queue_path = None
    generated = None
    collections = None
    
    def __init__(self, base_dir):
        """
        @param base_dir: str Absolute path
        """
        self.base_dir = os.path.normpath(base_dir)
        self.lock_path = lock_path(self.base_dir)
        self.queue_path = queue_path(self.base_dir)
        if os.path.exists(self.queue_path):
            self.read()
    
    def status_paths(self):
        """Returns list of collection_ids for which there are gitstatus files.
        
        >>> q = GitstatusQueue('/var/www/media/ddr')
        >>> q.status_paths()
        ['/var/www/media/ddr/tmp/ddr-densho-10.status',
        '/var/www/media/ddr/tmp/ddr-densho-101.status', ...]
        
        @returns: list of status file paths
        """
        pattern = re.compile('\w+-\w+-\d+.status')
        workdir = tmp_dir(self.base_dir)
        statuses = [os.path.join(workdir, f) for f in os.listdir(workdir) if pattern.match(f)]
        statuses.sort()
        return statuses
    
    def lock(self, task_id):
        """Sets a lock to prevent update_store from running
        
        Multiple locks can be set. Locks are added to the lockfile
        and removed on unlock. This helps avoid a race condition:
        - Task A locks.
        - Task B locks.
        - Task B unlocks, removing lockfile.
        - GitstatusQueue.update() thinks it's okay to run.
        
        >>> q = GitstatusQueue('/var/www/media/ddr')
        >>> q.lock_path
        '/var/www/media/ddr/tmp/gitstatus-lock'
        >>> os.path.exists(q.lock_path)
        False
        >>> q.locked_global()
        False
        >>> q.lock('1234')
        '2016-01-27T10:41:27:085684 1234'
        >>> os.path.exists(q.lock_path)
        True
        >>> q.locked_global()
        ['2016-01-27T10:41:27:085684 1234']
        >>> q.lock('1248')
        '2016-01-27T10:41:27:085684 1234\n2016-01-27T10:42:16:969253 1248'
        >>> q.locked_global()
        ['2016-01-27T10:41:27:085684 1234\n', '2016-01-27T10:42:16:969253 1248']
        >>> q.unlock('1234')
        '2016-01-27T10:42:16:969253 1248'
        >>> q.lock('1248')
        ''
        >>> os.path.exists(q.lock_path)
        False
        >>> q.locked_global()
        False
        
        TODO Other parts of the app may want to do this too
        
        @param task_id: Unique identifier for task.
        @returns: Complete text of lockfile
        """
        ts = datetime.now().strftime(settings.TIMESTAMP_FORMAT)
        text = '%s %s' % (ts, task_id)
        locks = []
        if os.path.exists(self.lock_path):
            with open(self.lock_path, 'r') as f:
                locks = f.readlines()
        already = None
        for lock in locks:
            lock = lock.strip()
            if lock:
                ts,tsk = lock.split(' ', 1)
                if task_id == tsk:
                    already = True
        if not already:
            locks.append(text)
        cleaned = [lock.strip() for lock in locks]
        lockfile_text = '\n'.join(cleaned)
        with open(self.lock_path, 'w') as f:
            f.write(lockfile_text)
        return lockfile_text
    
    def unlock(self, task_id):
        """Removes specified lock and allows update_store to run again
        
        See docs for lock().
        
        @param task_id: Unique identifier for task.
        @returns: Complete text of lockfile
        """
        locks = []
        if os.path.exists(self.lock_path):
            with open(self.lock_path, 'r') as f:
                locks = f.readlines()
        remaining = []
        for lock in locks:
            lock = lock.strip()
            if lock:
                ts,tsk = lock.split(' ', 1)
                if not task_id == tsk:
                    remaining.append(lock)
        lockfile_text = '\n'.join(remaining)
        if lockfile_text:
            with open(self.lock_path, 'w') as f:
                f.write(lockfile_text)
        else:
            if os.path.exists(self.lock_path):
                os.remove(self.lock_path)
        return lockfile_text
     
    def locked_global(self):
        """Indicates whether gitstatus global lock is in effect.
        
        See docs for lock().
        
        @returns: True, False
        """
        if os.path.exists(self.lock_path):
            with open(self.lock_path, 'r') as f:
                locks = f.readlines()
            return locks
        return False
     
    def loads(self, text):
        """Load queue from string
        
        @param text: str
        """
        lines = text.strip().split('\n')
        self.generated = datetime.strptime(
            lines.pop(0).strip().split()[1],
            settings.TIMESTAMP_FORMAT
        )
        self.collections = []
        for line in lines:
            ts,collection_id = line.split()
            self.collections.append([
                datetime.strptime(ts, settings.TIMESTAMP_FORMAT),
                Identifier(collection_id, self.base_dir)
            ])
    
    def dumps(self):
        """Write queue to text; lines are ordered in ascending date order
         
        Sample file:
            generated 2014-07-10T10:19:00
            1969-12-31T23:59:59 ddr-test-231   <
            1969-12-31T23:59:59 ddr-test-123   < These have not been done yet.
            2014-07-10T10:19:00 ddr-test-231   < These have.
            2014-07-10T10:19:01 ddr-test-124   <
        
        @returns: str
        """
        lines = []
        for c in self.collections:
            lines.append(' '.join([
                c[0].strftime(settings.TIMESTAMP_FORMAT),
                c[1].id,
            ]))
        lines.sort()
        lines.insert(0, 'generated %s' % self.generated.strftime(settings.TIMESTAMP_FORMAT))
        return '\n'.join(lines) + '\n'
     
    def read(self):
        """Read queue from file.
        
        @returns: str
        """
        if os.path.exists(self.queue_path):
            with open(self.queue_path, 'r') as f:
                text = f.read()
            return self.loads(text)
     
    def write(self):
        """Write queue to file.
        if queue timestamp too old, queue_generate()
        """
        text = self.dumps()
        with open(self.queue_path, 'w') as f:
            f.write(text)
     
    def generate(self, repos_orgs):
        """Generates a new queue file
        
        @param repos_orgs: list of org IDs (e.g. output of gitolite.get_repos_orgs)
        @returns: queue understandable by queue_loads,  queue_dumps
        """
        log('regenerating gitstatus queue')
        self.generated = datetime.now()
        self.collections = []
        cids = []
        # gitstatuses
        for status_path in self.status_paths():
            gs = Gitstatus.from_status_path(status_path)
            gs.read()
            self.collections.append([
                gs.timestamp,
                gs.identifier
            ])
            cids.append(gs.identifier.id)
        # collections without gitstatuses
        epoch = datetime.fromtimestamp(0)
        for o in repos_orgs:
            repo,org = o.split('-')
            for path in Collection.collection_paths(self.base_dir, repo, org):
                cidentifier = Identifier(path)
                if not cidentifier.id in cids:
                    cids.append(cidentifier.id)
                    self.collections.append([
                        epoch,
                        cidentifier
                    ])
        self.generated = datetime.now()
     
    def mark_updated(self, gitstatus, delta, minimum):
        """Resets or adds collection timestamp and returns queue
        
        @param gitstatus: Gitstatus object
        @param delta: int (seconds) Delta added to highest available timestamp
        @param minimum: int (seconds) Minimum delta
        """
        timestamp = self.next_time(delta, minimum)
        present = False
        for line in self.collections:
            ts,cidentifier = line
            if cidentifier.id == gitstatus.identifier.id:
                line[0] = timestamp
                present = True
        if not present:
            self.collections.append([
                timestamp,
                gitstatus.identifier
            ])
     
    def next_time(self, delta, minimum):
        """Chooses the next earliest time a repo can be updated
        
        Chooses highest timestamp in queue plus ${delta},
        or at least ${now} + ${minimum}.
        
        @param delta: int (seconds) Delta added to highest available timestamp
        @param minimum: int (seconds) Minimum delta
        @returns: datetime
        """
        latest = None
        for ts,cidentifier in sorted(self.collections):
            if (not latest) or (ts > latest):
                latest = ts
        timestamp = latest + timedelta(seconds=delta)
        earliest = datetime.now() + timedelta(seconds=minimum)
        if timestamp < earliest:
            timestamp = earliest
        return timestamp
     
    def next_repo(self, local=False):
        """Gets next collection_path or time til next ready to be updated
            
        @param local: Boolean Use local per-collection locks or global lock.
        @returns: Identifier or (msg,timedelta)
        """
        collection_path = None
        message = None
        next_available = None
        # sorts collections in ascending order by timestamp
        collections = sorted(self.collections)
        # now choose
        if local:
            # choose first collection that is not locked
            for timestamp,cidentifier in collections:
                if datetime.now() > timestamp:
                    if not Collection.from_identifier(cidentifier).locked():
                        return cidentifier
                if (not next_available) or (timestamp < next_available):
                    next_available = timestamp
        else:
            # global lock - just take the first collection
            for timestamp,cidentifier in collections:
                if datetime.now() > timestamp:
                    return cidentifier
                if (not next_available) or (timestamp < next_available):
                    next_available = timestamp
        return ('notready',next_available)
    
    def update(self, delta, minimum, local=False):
        """Gets Git status for next collection, updates queue file.
        
        - Ensures only one gitstatus_update task running at a time
        - Checks to make sure MEDIA_BASE is readable and that no
          other process has requested a lock.
        - Pulls next collection_path off the queue.
        - Triggers a gitstatus update/write
        - 
        
        Reference: Ensuring only one gitstatus_update runs at a time
        http://docs.celeryproject.org/en/latest/tutorials/task-cookbook.html#cookbook-task-serial
        
        @param delta: int (seconds) Delta added to highest available timestamp
        @param minimum: int (seconds) Minimum delta
        @param local: boolean Use per-collection locks
        @returns: success/fail message
        """
        log('GitstatusQueue.update(%s, %s, %s)' % (delta, minimum, local))
        if not os.path.exists(self.base_dir):
            raise Exception('base_dir does not exist. No Store mounted?: %s' % self.base_dir)
        GITSTATUS_LOCK_ID = 'gitstatus-update-lock'
        GITSTATUS_LOCK_EXPIRE = 60 * 5
        acquire_lock = lambda: cache.add(GITSTATUS_LOCK_ID, 'true', GITSTATUS_LOCK_EXPIRE)
        release_lock = lambda: cache.delete(GITSTATUS_LOCK_ID)
        #logger.debug('git status: %s', collection_path)
        messages = []
        if acquire_lock():
            try:
                writable = is_writable(self.base_dir)
                if not writable:
                    msg = 'base_dir not writable: %s' % self.base_dir
                    messages.append(msg)
                
                locked = None
                if not local:
                    msg = 'using global lockfile'
                    messages.append(msg)
                    locked = self.locked_global()
                if locked:
                    msg = 'locked: %s' % locked
                    messages.append(msg)
                
                if writable and not locked:
                    self.read()
                    nextcoll = self.next_repo(local=local)
                    log(nextcoll)
                    if isinstance(nextcoll, list) or isinstance(nextcoll, tuple):
                        msg = 'next_repo %s' % str(nextcoll)
                        messages.append(msg)
                    elif isinstance(nextcoll, Identifier):
                        collection_path = nextcoll.path_abs()
                        gs = Gitstatus(Identifier(collection_path))
                        gs.update()
                        gs.write()
                        self.mark_updated(gs, delta, minimum)
                        self.write()
                        msg = 'updated %s' % gs.identifier
                        messages.append(msg)
                        
                
            finally:
                release_lock()
        else:
            messages.append("couldn't get celery lock")
            #logger.debug('git-status: another worker already running')
        #return 'git-status: another worker already running'
        return messages


def update_store(base_dir, delta, minimum, local=False):
    """Gets Git status for next collection, updates queue file.
    
    @param base_dir: 
    @param delta: int (seconds) Delta added to highest available timestamp
    @param minimum: int (seconds) Minimum delta
    @param local: boolean Use per-collection locks
    @returns: success/fail message
    """
    return GitstatusQueue(base_dir).update(delta, minimum, local)
