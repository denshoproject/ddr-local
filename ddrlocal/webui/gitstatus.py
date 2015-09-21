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
from webui.models import Identifier


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
    
def queue_path( base_dir ):
    return os.path.join(
        tmp_dir(base_dir),
        'gitstatus-queue'
    )
    
def lock_path( base_dir ):
    return os.path.join(
        tmp_dir(base_dir),
        'gitstatus-lock'
    )

def path( base_dir, collection_path ):
    """
    - STORE/status/ddr-test-123.status
    """
    return os.path.join(
        tmp_dir(base_dir),
        '%s.status' % os.path.basename(collection_path)
    )

def status_paths( base_dir ):
    """Returns list of collection_ids for which there are gitstatus files.
    """
    pattern = re.compile('\w+-\w+-\d+.status')
    workdir = tmp_dir(base_dir)
    statuses = [os.path.join(workdir, f) for f in os.listdir(workdir) if pattern.match(f)]
    statuses.sort()
    return statuses

def dumps( timestamp, elapsed, status, annex_status, syncstatus ):
    """Formats git-status,git-annex-status,sync-status and timestamp as text
    
    Sample:
        {timestamp} {elapsed}
        %%
        {status}
        %%
        {annex status}
        %%
        {sync status}
    """
    timestamp_elapsed = ' '.join([
        timestamp.strftime(settings.TIMESTAMP_FORMAT),
        str(elapsed)
    ])
    return '\n%%\n'.join([
        timestamp_elapsed,
        status,
        annex_status,
        json.dumps(syncstatus),
    ])

def loads( text ):
    """Converts status data from text to Python objects
    
    @returns: dict (keys: timestamp,elapsed,status,annex_status,syncstatus)
    """
    # we don't know in advance how many fields exist in .gitstatus
    # so get as many as we can
    variables = [None,None,None,None]
    for n,part in enumerate(text.split('%%')):
        variables[n] = part.strip()
    meta = variables[0]
    if meta:
        ts,elapsed = meta.split(' ')
        timestamp = datetime.strptime(ts, settings.TIMESTAMP_FORMAT)
    status = variables[1]
    annex_status = variables[2]
    syncstatus = variables[3]
    if syncstatus: # may not be present
        syncstatus = json.loads(syncstatus)
        if syncstatus.get('timestamp',None):
            syncstatus['timestamp'] = datetime.strptime(syncstatus['timestamp'], settings.TIMESTAMP_FORMAT)
    return {
        'timestamp': timestamp,
        'elapsed': elapsed,
        'status': status,
        'annex_status': annex_status,
        'sync_status': syncstatus,
    }

def write( base_dir, collection_path, timestamp, elapsed, status, annex_status, syncstatus ):
    """Writes .gitstatus for the collection; see format.
    """
    text = dumps(timestamp, elapsed, status, annex_status, syncstatus) + '\n'
    with open(path(base_dir, collection_path), 'w') as f:
        f.write(text)
    return text

def read( base_dir, collection_path ):
    """Reads .gitstatus for the collection and returns parsed data.
    """
    if os.path.exists(path(base_dir, collection_path)):
        with open(path(base_dir, collection_path), 'r') as f:
            text = f.read()
        data = loads(text)
        return data
    return None

COLLECTION_SYNC_STATUS_CACHE_KEY = 'webui:collection:%s:sync-status'

def sync_status( collection_path, git_status, timestamp, cache_set=False, force=False ):
    """Cache collection repo sync status info for collections list page.
    Used in both .collections() and .sync_status_ajax().
    
    TODO do we need to cache this any more? we're writing this to REPO/.gitstatus
    
    @param collection: 
    @param cache_set: Run git-status if data is not cached
    """
    # IMPORTANT: DO NOT call collection.gitstatus() it will loop
    collection_id = Identifier.from_path(collection_path)
    key = COLLECTION_SYNC_STATUS_CACHE_KEY % collection_id
    data = cache.get(key)
    if force or (not data and cache_set):
        status = 'unknown'
        btn = 'muted'
        # we're just getting this so we can call Collection.locked
        disposable_collection = Collection(path=collection_path)
        # now:
        if   dvcs.ahead(git_status): status = 'ahead'; btn = 'warning'
        elif dvcs.behind(git_status): status = 'behind'; btn = 'warning'
        elif dvcs.conflicted(git_status): status = 'conflicted'; btn = 'danger'
        elif dvcs.synced(git_status): status = 'synced'; btn = 'success'
        elif disposable_collection.locked(): status = 'locked'; btn = 'warning'
        if isinstance(timestamp, datetime):
            timestamp = timestamp.strftime(settings.TIMESTAMP_FORMAT)
        data = {
            'row': '#%s' % collection_id,
            'color': btn,
            'cell': '#%s td.status' % collection_id,
            'status': status,
            'timestamp': timestamp,
        }
        cache.set(key, data, COLLECTION_STATUS_TIMEOUT)
    return data

def update( base_dir, collection_path ):
    """Gets a bunch of status info for the collection; refreshes if forced
    
    timestamp, elapsed, status, annex_status, syncstatus
    
    @param force: Boolean Forces refresh of status
    @returns: dict
    """
    start = datetime.now()
    status = dvcs.repo_status(collection_path, short=True)
    annex_status = dvcs.annex_status(collection_path)
    timestamp = datetime.now()
    syncstatus = sync_status(collection_path, git_status=status, timestamp=timestamp, force=True)
    elapsed = timestamp - start
    text = write(base_dir, collection_path, timestamp, elapsed, status, annex_status, syncstatus)
    return loads(text)



def lock( base_dir, task_id ):
    """Sets a lock to prevent update_store from running
    
    Multiple locks can be set. Locks are added to the lockfile
    and removed on unlock. This helps avoid a race condition:
    - Task A locks.
    - Task B locks.
    - Task B unlocks, removing lockfile.
    - gitstatus.update_store() thinks it's okay to run.
    
    >>> basedir = '/tmp/gitstatus'
    >>> lockpath = lock_path(basedir)
    >>> os.path.exists(lockpath)
    False
    >>> locked_global(basedir)
    False
    >>> lock(basedir, '1234')
    '2014-07-15T15:17:15:254884 1234'
    >>> os.path.exists(lockpath)
    True
    >>> locked_global(basedir)
    '2014-07-15T15:17:15:254884 1234'
    >>> lock(basedir, '1248')
    '2014-07-15T15:17:15:254884 1234\n2014-07-15T15:17:15:254907 1248'
    >>> locked_global(basedir)
    '2014-07-15T15:17:15:254884 1234\n2014-07-15T15:17:15:254907 1248'
    >>> unlock(basedir, '1234')
    '2014-07-15T15:17:15:254907 1248'
    >>> lock(basedir, '1248')
    ''
    >>> os.path.exists(lockpath)
    False
    >>> locked_global(basedir)
    False
    
    TODO Other parts of the app may want to do this too
    
    @param task_id: Unique identifier for task.
    @returns: Complete text of lockfile
    """
    ts = datetime.now().strftime(settings.TIMESTAMP_FORMAT)
    text = '%s %s' % (ts, task_id)
    LOCK = lock_path(base_dir)
    locks = []
    if os.path.exists(LOCK):
        with open(LOCK, 'r') as f:
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
    with open(LOCK, 'w') as f:
        f.write(lockfile_text)
    return lockfile_text

def unlock( base_dir, task_id ):
    """Removes specified lock and allows update_store to run again
    
    See docs for lock().
    
    @param task_id: Unique identifier for task.
    @returns: Complete text of lockfile
    """
    LOCK = lock_path(base_dir)
    locks = []
    if os.path.exists(LOCK):
        with open(LOCK, 'r') as f:
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
        with open(LOCK, 'w') as f:
            f.write(lockfile_text)
    else:
        if os.path.exists(LOCK):
            os.remove(LOCK)
    return lockfile_text

def locked_global( base_dir ):
    """Indicates whether gitstatus global lock is in effect.
    
    See docs for lock().
    
    @returns: True, False
    """
    LOCK = lock_path(base_dir)
    if os.path.exists(LOCK):
        with open(LOCK, 'r') as f:
            locks = f.readlines()
        return locks
    return False

def queue_loads( text ):
    """Load queue from string
    
    >>> queue_read()
    {
        'generated': datetime(2014-07-10T10:19:00),
        'collections': [
            [datetime(1969,12,31,23,59,59), 'ddr-test-231'],
            [datetime(1969,12,31,23,59,59), 'ddr-test-123'],
            [datetime(2014,07,10,10,19,00), 'ddr-test-231'],
            [datetime(2014,07,10,10,19,01), 'ddr-test-124'],
        ]
    }
    """
    lines = text.strip().split('\n')
    generated = datetime.strptime(lines.pop(0).strip().split()[1], settings.TIMESTAMP_FORMAT)
    queue = {'generated':generated, 'collections':[]}
    for line in lines:
        ts,collection_id = line.split()
        timestamp = datetime.strptime(ts, settings.TIMESTAMP_FORMAT)
        queue['collections'].append( [timestamp,collection_id] )
    return queue

def queue_dumps( queue ):
    """Write queue to text; lines are ordered in ascending date order
     
    Sample file:
        generated 2014-07-10T10:19:00
        1969-12-31T23:59:59 ddr-test-231   <
        1969-12-31T23:59:59 ddr-test-123   < These have not been done yet.
        2014-07-10T10:19:00 ddr-test-231   < These have.
        2014-07-10T10:19:01 ddr-test-124   <
    """
    lines = []
    for c in queue['collections']:
        lines.append(' '.join([
            c[0].strftime(settings.TIMESTAMP_FORMAT),
            c[1],
        ]))
    lines.sort()
    lines.insert(0, 'generated %s' % queue['generated'].strftime(settings.TIMESTAMP_FORMAT))
    return '\n'.join(lines) + '\n'

def queue_read( base_dir ):
    """Read queue from file.
    """
    path = queue_path(base_dir)
    assert os.path.exists(path)
    with open(path, 'r') as f:
        text = f.read()
    return queue_loads(text)

def queue_write( base_dir, queue ):
    """Write queue to file.
    if queue timestamp too old, queue_generate()
    """
    path = queue_path(base_dir)
    text = queue_dumps(queue)
    with open(path, 'w') as f:
        f.write(text)

def queue_generate( base_dir, repos_orgs ):
    """Generates a new queue file
    
    @param base_dir: Absolute path to Store dir
    @param repos_orgs: Output of gitolite.get_repos_orgs.
    @returns: queue understandable by queue_loads,  queue_dumps
    """
    log('regenerating gitstatus queue')
    queue = {'collections': []}
    cids = []
    # gitstatuses
    for path in status_paths(base_dir):
        collection_id = path.replace(tmp_dir(base_dir), '').replace('/','').replace('.status', '')
        status = read(base_dir, collection_id)  # read timestamp from .status file
        queue['collections'].append( (status['timestamp'],collection_id) )
        cids.append(collection_id)
    # collections without gitstatuses
    epoch = datetime.fromtimestamp(0)
    for o in repos_orgs:
        repo,org = o.split('-')
        for path in Collection.collection_paths(base_dir, repo, org):
            collection_id = os.path.basename(path)
            if not collection_id in cids:
                cids.append(collection_id)
                queue['collections'].append( (epoch,collection_id) )
    queue['generated'] = datetime.now()
    return queue

def queue_mark_updated( queue, collection_id, delta, minimum ):
    """Resets or adds collection timestamp and returns queue
    
    @param queue
    @param collection_id
    @param delta: int (seconds) Delta added to highest available timestamp
    @param minimum: int (seconds) Minimum delta
    @returns: queue with updated collection timestamp
    """
    timestamp = next_time(queue, delta, minimum)
    present = False
    for line in queue['collections']:
        ts,cid = line
        if cid == collection_id:
            line[0] = timestamp
            present = True
    if not present:
        queue['collections'].append([timestamp, collection_id])
    return queue

def next_time( queue, delta, minimum ):
    """Chooses the next earliest time a repo can be updated
    
    Chooses highest timestamp in queue plus ${delta},
    or at least ${now} + ${minimum}.
    
    @param queue
    @param delta: int (seconds) Delta added to highest available timestamp
    @param minimum: int (seconds) Minimum delta
    @returns: datetime
    """
    latest = None
    for ts,cid in sorted(queue['collections']):
        if (not latest) or (ts > latest):
            latest = ts
    timestamp = latest + timedelta(seconds=delta)
    earliest = datetime.now() + timedelta(seconds=minimum)
    if timestamp < earliest:
        timestamp = earliest
    return timestamp

def next_repo( queue, local=False ):
    """Gets next collection_path or time til next ready to be updated
        
    @param queue: 
    @param local: Boolean Use local per-collection locks or global lock.
    @returns: collection_path or (msg,timedelta)
    """
    collection_path = None
    message = None
    next_available = None
    # sorts collections in ascending order by timestamp
    collections = sorted(queue['collections'])
    # now choose
    if local:
        # choose first collection that is not locked
        for timestamp,cid in collections:
            if datetime.now() > timestamp:
                collection = Collection.from_identifier(Identifier.from_id(cid))
                if not collection.locked():
                    return collection.path_abs
            if (not next_available) or (timestamp < next_available):
                next_available = timestamp
    else:
        # global lock - just take the first collection
        for timestamp,cid in collections:
            if datetime.now() > timestamp:
                identifier = Identifier.from_id(cid)
                return identifier.path_abs
            if (not next_available) or (timestamp < next_available):
                next_available = timestamp
    return ('notready',next_available)

def update_store( base_dir, delta, minimum, local=False ):
    """
    
    - Ensures only one gitstatus_update task running at a time
    - Checks to make sure MEDIA_BASE is readable and that no
      other process has requested a lock.
    - Pulls next collection_path off the queue.
    - Triggers a gitstatus update/write
    - 
    
    Reference: Ensuring only one gitstatus_update runs at a time
    http://docs.celeryproject.org/en/latest/tutorials/task-cookbook.html#cookbook-task-serial
    
    @param base_dir: 
    @param delta: int (seconds) Delta added to highest available timestamp
    @param minimum: int (seconds) Minimum delta
    @param local: boolean Use per-collection locks
    @returns: success/fail message
    """
    if not os.path.exists(base_dir):
        raise Exception('base_dir does not exist. No Store mounted?: %s' % base_dir)
    GITSTATUS_LOCK_ID = 'gitstatus-update-lock'
    GITSTATUS_LOCK_EXPIRE = 60 * 5
    acquire_lock = lambda: cache.add(GITSTATUS_LOCK_ID, 'true', GITSTATUS_LOCK_EXPIRE)
    release_lock = lambda: cache.delete(GITSTATUS_LOCK_ID)
    #logger.debug('git status: %s', collection_path)
    messages = []
    if acquire_lock():
        try:
            writable = is_writable(base_dir)
            if not writable:
                log('base_dir not writable: %s' % base_dir)
                messages.append('base_dir not writable: %s' % base_dir)
            
            locked = None
            if not local:
                messages.append('using global lockfile')
                locked = locked_global(base_dir)
            if locked:
                messages.append('locked: %s' % locked)
            
            if writable and not locked:
                collection_path = None
                queue = queue_read(base_dir)
                response = next_repo(queue, local=local)
                if isinstance(response, list) or isinstance(response, tuple):
                    messages.append('next_repo %s' % str(response))
                elif isinstance(response, basestring) and os.path.exists(response):
                    collection_path = response
                if collection_path:
                    timestamp,elapsed,status,annex_status,syncstatus = update(base_dir, collection_path)
                    # TODO use Identifier
                    collection_id = os.path.basename(collection_path)
                    queue = queue_mark_updated(queue, collection_id, delta, minimum)
                    queue_write(base_dir, queue)
                    messages.append('%s updated' % (collection_path))
            
        finally:
            release_lock()
    else:
        log("couldn't get celery lock")
        messages.append("couldn't get celery lock")
        #logger.debug('git-status: another worker already running')
    #return 'git-status: another worker already running'
    return messages
