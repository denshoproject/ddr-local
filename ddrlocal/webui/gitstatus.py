from datetime import datetime
import json
import os
import time

from celery import task
from celery.utils.log import get_task_logger

from django.conf import settings
from django.core.cache import cache
#from django.utils.hashcompat import md5_constructor as md5

from webui.models import Collection
from DDR import storage


GITSTATUS_QUEUE_PATH = os.path.join(settings.MEDIA_BASE, '.gitstatus-queue')
GITSTATUS_LOCK_PATH = os.path.join(settings.MEDIA_BASE, '.gitstatus-stop')
GITSTATUS_INTERVAL = 10

def gitstatus_loop():
    """
    """
    # check for active/mounted device
    writable = storage.is_writable(settings.MEDIA_BASE)
    # checks if heavy-task-lock set
    locked = gitstatus_locked()
    while writable and not locked:
        gitstatus_update()
        time.sleep(GITSTATUS_INTERVAL)
        locked = gitstatus_locked()

def gitstatus_lock():
    if not os.path.exists(GITSTATUS_LOCK_PATH):
        now = datetime.now().strftime(settings.TIMESTAMP_FORMAT)
        with open(GITSTATUS_LOCK_PATH, 'w') as f:
            f.write(now)

def gitstatus_unlock():
    if os.path.exists(GITSTATUS_LOCK_PATH):
        os.remove(GITSTATUS_LOCK_PATH)

def gitstatus_locked():
    if os.path.exists(GITSTATUS_LOCK_PATH):
        return True
    return False

def gitstatus_kill():
    pass

def gitstatus_next_repo():
    """Gets next collection_path from gitstatus queue.
    """
    collection_path = None
    data = None
    
    if os.path.exists(GITSTATUS_QUEUE_PATH):
        print('reading %s' % GITSTATUS_QUEUE_PATH)
        with open(GITSTATUS_QUEUE_PATH, 'r') as f:
            data = json.loads(f.read())
    else:
        print('creating %s' % GITSTATUS_QUEUE_PATH)
        # make a new list
        data = []
        with open(GITSTATUS_QUEUE_PATH, 'w') as f1:
            f1.write(json.dumps(data))
    
    print('data: %s' % data)
    if len(data) == 0:
        print('refreshing')
        data = find_updateable_repos('ddr', 'densho')
        print('data: %s' % data)
    
    data.reverse()
    collection_path = data.pop()
    print(collection_path)
    data.reverse()
    with open(GITSTATUS_QUEUE_PATH, 'w') as f1:
        f1.write(json.dumps(data))

    # remove collection_path now that we've read it
    return collection_path

def find_updateable_repos(repo, org):
    repos = Collection.collections(settings.MEDIA_BASE, repository=repo, organization=org)
    return repos


GITSTATUS_LOCK_ID = 'gitstatus-update-lock'
GITSTATUS_LOCK_EXPIRE = 60 * 5 # Lock expires in 5 minutes

#@task(name='gitstatus-update')
def gitstatus_update():
    """
    ENSURING A TASK IS ONLY EXECUTED ONE AT A TIME
    http://docs.celeryproject.org/en/latest/tutorials/task-cookbook.html#cookbook-task-serial
    """
    # cache.add fails if if the key already exists
    acquire_lock = lambda: cache.add(GITSTATUS_LOCK_ID, 'true', GITSTATUS_LOCK_EXPIRE)
    
    # cache delete is very slow, but we have to use it to take
    # advantage of using add() for atomic locking
    release_lock = lambda: cache.delete(GITSTATUS_LOCK_ID)
    
    #logger.debug('git status: %s', collection_path)
    git_status = None
    if acquire_lock():
        try:
            collection_path = gitstatus_next_repo()
            collection = Collection.from_json(collection_path)
            git_status = collection.repo_status(force=True)
        finally:
            release_lock()
        return collection_path,git_status
    
    #logger.debug('git-status: another worker already running')
    return 'git-status: another worker already running'

def gitstatus_update_revoke():
    """
    finds any 'gitstatus-update' and revokes
    references:
    http://docs.celeryproject.org/en/latest/reference/celery.events.state.html
    http://docs.celeryproject.org/en/latest/userguide/workers.html#revoking-tasks
    """
    # retrieve tasks and kill them
    query = celery.events.state.tasks_by_type('gitstatus-update')
    for uuid, task in query:
        celery.control.revoke(uuid, terminate=True)
