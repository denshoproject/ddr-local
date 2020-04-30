import os

from celery import task
from celery import Task
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from django.conf import settings

from webui import gitolite
from webui import gitstatus


class DebugTask(Task):
    abstract = True


# ----------------------------------------------------------------------

@task(base=DebugTask, name='webui.tasks.gitolite_info_refresh')
def gitolite_info_refresh():
    """
    Check the cached value of DDR.dvcs.gitolite_info().
    If it is stale (e.g. timestamp is older than cutoff)
    then hit the Gitolite server for an update and re-cache.
    """
    return gitolite.get_repos_orgs()


# ----------------------------------------------------------------------

class GitStatusTask(Task):
    abstract = True
        
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        pass
    
    def on_success(self, retval, task_id, args, kwargs):
        pass
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        logger.debug('GitStatusTask.after_return(%s, %s, %s, %s, %s, %s)' % (status, retval, task_id, args, kwargs, einfo))
        gitstatus.log('GitStatusTask.after_return(%s, %s, %s, %s, %s, %s)' % (status, retval, task_id, args, kwargs, einfo))

@task(base=GitStatusTask, name='webui.tasks.gitstatus_update')
def gitstatus_update( collection_path ):
    if not os.path.exists(settings.MEDIA_BASE):
        raise Exception('base_dir does not exist. No Store mounted?: %s' % settings.MEDIA_BASE)
    if not os.path.exists(gitstatus.queue_path(settings.MEDIA_BASE)):
        queue = gitstatus.queue_generate(
            settings.MEDIA_BASE,
            gitolite.get_repos_orgs()
        )
        gitstatus.queue_write(settings.MEDIA_BASE, queue)
    return gitstatus.update(settings.MEDIA_BASE, collection_path)

@task(base=GitStatusTask, name='webui.tasks.gitstatus_update_store')
def gitstatus_update_store():
    if not os.path.exists(settings.MEDIA_BASE):
        raise Exception('base_dir does not exist. No Store mounted?: %s' % settings.MEDIA_BASE)
    if not os.path.exists(gitstatus.queue_path(settings.MEDIA_BASE)):
        queue = gitstatus.queue_generate(
            settings.MEDIA_BASE,
            gitolite.get_repos_orgs()
        )
        gitstatus.queue_write(settings.MEDIA_BASE, queue)
    return gitstatus.update_store(
        base_dir=settings.MEDIA_BASE,
        delta=60,
        minimum=settings.GITSTATUS_INTERVAL,
    )
