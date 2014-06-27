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
"""

from datetime import datetime, timedelta
import json
import os

from django.conf import settings
from django.core.cache import cache

from DDR import dvcs
from DDR.storage import is_writable
from DDR.models import Collection, id_from_path
from webui import get_repos_orgs
from webui import COLLECTION_STATUS_TIMEOUT


def log(msg):
    """celery does not like writing to logs, so write to separate logfile
    """
    entry = '%s %s\n' % (datetime.now().strftime(settings.TIMESTAMP_FORMAT), msg)
    with open(settings.GITSTATUS_LOG, 'a') as f:
        f.write(entry)

def path( collection_path ):
    return os.path.join(collection_path, '.gitstatus')

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

def write( collection_path, timestamp, elapsed, status, annex_status, syncstatus ):
    """Writes .gitstatus for the collection; see format.
    """
    text = dumps(timestamp, elapsed, status, annex_status, syncstatus) + '\n'
    with open(path(collection_path), 'w') as f:
        f.write(text)
    return text

def read( collection_path ):
    """Reads .gitstatus for the collection and returns parsed data.
    """
    if os.path.exists(path(collection_path)):
        with open(path(collection_path), 'r') as f:
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
    collection_id = id_from_path(collection_path)
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

def update( collection_path ):
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
    text = write(collection_path, timestamp, elapsed, status, annex_status, syncstatus)
    return loads(text)

def lock( msg ):
    """Sets a lock that prevents update_store from running
    """
    text = None
    if not os.path.exists(settings.GITSTATUS_LOCK_PATH):
        ts = datetime.now().strftime(settings.TIMESTAMP_FORMAT)
        text = '%s %s' % (ts, msg)
        with open(settings.GITSTATUS_LOCK_PATH, 'w') as f:
            f.write(text)
    return text

def unlock():
    """Removes lock and allows update_store to run again
    """
    if os.path.exists(settings.GITSTATUS_LOCK_PATH):
        os.remove(settings.GITSTATUS_LOCK_PATH)
        if not os.path.exists(settings.GITSTATUS_LOCK_PATH):
            return True
        else:
            return False
    return None

def locked():
    """
    """
    if os.path.exists(settings.GITSTATUS_LOCK_PATH):
        with open(settings.GITSTATUS_LOCK_PATH, 'r') as f:
            text = f.read()
        return text
    return False

def next_repo():
    """Gets next collection_path or time til next ready to be updated
    
    Each line of GITSTATUS_QUEUE_PATH contains a collection_path and
    a timestamp of the last time git-status was done on the collection.
    Timestamps come from .gitstatus files in the collection repos.
    If a repo has no .gitstatus file then date in past is used (e.g. update now).
    The first collection with a timestamp more than GITSTATUS_INTERVAL
    in the past is returned.
    If there are collections but they are too recent a 'notready'
    message is returned along with the time til next is available.
    
    Sample file 0:
        [empty]
    
    Sample file 1:
        /var/www/media/base/ddr-densho-252 2014-06-24T1503:22-07:00
        /var/www/media/base/ddr-densho-255 2014-06-24T1503:22-07:00
        /var/www/media/base/ddr-densho-282 2014-06-24T1503:22-07:00
    
    @returns: collection_path or (msg,timedelta)
    """
    # load existing queue; populate queue if empty
    contents = ''
    if os.path.exists(settings.GITSTATUS_QUEUE_PATH):
        with open(settings.GITSTATUS_QUEUE_PATH, 'r') as f:
            contents = f.read()
    lines = []
    for line in contents.strip().split('\n'):
        line = line.strip()
        if line:
            lines.append(line)
    if not lines:
        # refresh
        for o in get_repos_orgs():
            repo,org = o.split('-')
            paths = Collection.collections(settings.MEDIA_BASE, repository=repo, organization=org)
            for path in paths:
                # get time repo gitstatus last update
                # if no gitstatus file, make immediately updatable
                gs = read(path)
                if gs:
                    ts = gs['timestamp'].strftime(settings.TIMESTAMP_FORMAT)
                else:
                    ts = datetime.fromtimestamp(0).strftime(settings.TIMESTAMP_FORMAT)
                line = ' '.join([path, ts])
                lines.append(line)
#    # if backoff leave the queue file as is
#    gitstatus_backoff = timedelta(seconds=settings.GITSTATUS_BACKOFF)
#    for n,line in enumerate(lines):
#        if 'backoff' in line:
#            msg,ts = line.split(' ')
#            timestamp = datetime.strptime(ts, settings.TIMESTAMP_FORMAT)
#            elapsed = datetime.now() - timestamp
#            if elapsed < gitstatus_backoff:
#                # not enough time elapsed: die
#                delay = gitstatus_backoff - elapsed
#                return 'backoff',delay
#            else:
#                # enough time has passed: rm the backoff
#                lines.remove(line)
    # any eligible collections?
    eligible = []
    gitstatus_interval = timedelta(seconds=settings.GITSTATUS_INTERVAL)
    delay = gitstatus_interval
    for line in lines:
        path,ts = line.split(' ')
        timestamp = datetime.strptime(ts, settings.TIMESTAMP_FORMAT)
        elapsed = datetime.now() - timestamp
        if elapsed > gitstatus_interval:
            eligible.append(line)
        else:
            # report smallest interval (e.g. next possible update time)
            wait = gitstatus_interval - elapsed
            if wait < delay:
               delay = wait
    # we have collections
    if lines:
        if eligible:
            # eligible collections - pop the first one off the queue
            for line in lines:
                if line == eligible[0]:
                    lines.remove(line)
            text = '\n'.join(lines) + '\n'
            with open(settings.GITSTATUS_QUEUE_PATH, 'w') as f1:
                f1.write(text)
            collection_path,ts = eligible[0].split(' ')
            return collection_path
        else:
#            # collections but none eligible: back off!
#            timestamp = datetime.now()
#            backoff = 'backoff %s' % timestamp.strftime(settings.TIMESTAMP_FORMAT)
#            lines.insert(0, backoff)
            text = '\n'.join(lines) + '\n'
            with open(settings.GITSTATUS_QUEUE_PATH, 'w') as f1:
                f1.write(text)
            return 'notready',delay
    return None

def update_store():
    """
    
    - Ensures only one gitstatus_update task running at a time
    - Checks to make sure MEDIA_BASE is readable and that no
      other process has requested a lock.
    - Pulls next collection_path off the queue.
    - Triggers a gitstatus update/write
    - 
    
    Reference: Ensuring only one gitstatus_update runs at a time
    http://docs.celeryproject.org/en/latest/tutorials/task-cookbook.html#cookbook-task-serial
    
    @returns: success/fail message
    """
    log('update_store() ---------------------')
    GITSTATUS_LOCK_ID = 'gitstatus-update-lock'
    GITSTATUS_LOCK_EXPIRE = 60 * 5
    acquire_lock = lambda: cache.add(GITSTATUS_LOCK_ID, 'true', GITSTATUS_LOCK_EXPIRE)
    release_lock = lambda: cache.delete(GITSTATUS_LOCK_ID)
    #logger.debug('git status: %s', collection_path)
    message = None
    if acquire_lock():
        log('celery lock acquired')
        try:
            writable = is_writable(settings.MEDIA_BASE)
            lockd = locked()
            if lockd:
                message = 'locked: %s' % lockd
                log(message)
            elif writable:
                response = next_repo()
                log(response)
                if isinstance(response, list) or isinstance(response, tuple):
                    message = str(response)
                else:
                    collection_path = response
                    timestamp,elapsed,status,annex_status,syncstatus = update(collection_path)
                    message = '%s updated' % (collection_path)
            else:
                log('MEDIA_BASE not writable!')
                message = 'MEDIA_BASE not writable!'
        finally:
            release_lock()
            log('celery lock released')
    else:
        log("couldn't get celery lock")
        message = "couldn't get celery lock"
        #logger.debug('git-status: another worker already running')
    #return 'git-status: another worker already running'
    return message
