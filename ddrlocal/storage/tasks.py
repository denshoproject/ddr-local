from celery import states
from celery import task
from celery import Task
from celery.result import AsyncResult
from celery.utils import get_full_cls_name
from celery.utils.encoding import safe_repr
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from django.conf import settings
from django.contrib import messages

from DDR import commands
import storage


class DebugTask(Task):
    abstract = True

class StorageTask(Task):
    abstract = True
        
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.debug('on_failure(%s, %s, %s, %s)' % (exc, task_id, args, kwargs))
    
    def on_success(self, retval, task_id, args, kwargs):
        logger.debug('on_success(%s, %s, %s, %s)' % (retval, task_id, args, kwargs))
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        logger.debug('after_return(%s, %s, %s, %s, %s)' % (status, retval, task_id, args, kwargs))

@task(base=StorageTask, name='storage.tasks.mount')
def mount_in_bkgnd(devicetype, devicefile):
    device = None
    for d in storage.devices():
        if d['devicefile'] == devicefile:
            device = d
    if not device:
        raise Exception('Device %s not in list of devices' % devicefile)
    
    if devicetype == 'hd':
        assert False
    elif devicetype == 'usb':
        return mount_usb(device)
    return

def mount_usb(device):
    """Mounts requested device, adds /var/www/ddr/media symlink, gives feedback.
    """
    actions = []
    logger.debug('mount_usb(devicefile=%s, label=%s)' % (device['devicefile'], device['label']))
    logger.debug('device: %s' % device)
    stat,mount_path = commands.mount(device['devicefile'], device['label'])
    actions.append(mount_path)
    logger.debug('stat: %s' % stat)
    logger.debug('mount_path: %s' % mount_path)
    if mount_path:
        logger.debug('rm existing symlink')
        storage.rm_media_symlink()
        if device.get('mountpath'):
            logger.debug('new symlink')
            storage.add_media_symlink(device['mountpath'])
            logger.debug('OK')
    logger.debug('done')
            
