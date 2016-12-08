import logging
logger = logging.getLogger(__name__)
import os

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache

from DDR import docstore
from DDR import storage as ddrstorage


STORAGE_MESSAGES = {
    # storage.__init__
    'MOUNT_ERR_MISSING_INFO': 'storage.mount(): devicefile or label missing [{} {}]', # devicefile, label
    'MOUNT_SUCCESS': 'Mounted {}', # label
    'MOUNT_FAIL_PATH': 'Count not mount device  [{} {}: {},{}]', # devicefile, label, stat, mount_path
    'MOUNT_FAIL':      'Problem mounting device [{} {}: {},{}]', # devicefile, label, stat, mount_path
    'UNMOUNT_SUCCESS': 'Umounted {}', # label
    'UNMOUNT_FAIL_1': 'Count not unmount device  [{} {}: {},{}]', # devicefile, label, stat, mounted
    'UNMOUNT_FAIL':   'Problem unmounting device [{} {}: {},{}]', # devicefile, label, stat, mounted
    
    # storage.decorators
    'NO_REPOS_ORGS': 'ERROR: No repos/orgs from gitolite_info function. Missing or invalid SSH keys?',
    'ERROR': 'ERROR: Could not get list of collections. Is USB HDD plugged in?',
    
    # storage.views
    'REMOUNT_FAIL': 'Unable to attempt remount. Please remount manually.',
    
}



BASE_PATH_TIMEOUT = 60 * 30  # 30 min
BASE_PATH_DEFAULT = '/tmp/ddr'
DISK_SPACE_TIMEOUT = 60 * 5
DISK_SPACE_CACHE_KEY = 'ddrlocal:disk_space'


def base_path(request=None):
    """The actual base path to the Repository; includes USB device name.
    
    We don't know this in advance.
    We also don't want the user to have to edit a settings file in order
    to use a different device.
    
    MEDIA_ROOT, which is used by the rest of the application and by
    the www server, uses the symlink managed by ddrstorage.link() and
    ddrstorage.unlink().
    
    Expected result: '/media/WD5000BMV-2/ddr' or similar.
    
    @param request: Django Request object
    @returns: str absolute path to directory containing collection repos
    """
    key = 'ddrlocal:base_path'
    path = cache.get(key)
    if path and (path != BASE_PATH_DEFAULT):
        #logger.debug('base_path != %s' % BASE_PATH_DEFAULT)
        # expires %{BASE_PATH_TIMEOUT} after last access
        cache.set(key, path, BASE_PATH_TIMEOUT)
    else:
        mount_path = None
        path = BASE_PATH_DEFAULT
        if request:
            mount_path = request.session.get('storage_mount_path', None)
        if mount_path:
            logger.debug('mount_path: %s' % mount_path)
            if not (os.path.basename(mount_path) == settings.DDR_USBHDD_BASE_DIR):
                path = os.path.join(mount_path, settings.DDR_USBHDD_BASE_DIR)
            logger.debug('caching: %s' % path)
            cache.set(key, path, BASE_PATH_TIMEOUT)
    return path

def devices():
    return ddrstorage.devices(symlink=settings.MEDIA_BASE)

def mounted_devices():
    return ddrstorage.mounted_devices()

def disk_space(mount_path):
    space = cache.get(DISK_SPACE_CACHE_KEY)
    if mount_path and os.path.exists(mount_path) and not space:
        space = ddrstorage.disk_space(mount_path)
        cache.set(DISK_SPACE_CACHE_KEY, space, DISK_SPACE_TIMEOUT)
    return space

def _mount_common(request, device):
    # save label,mount_path in session
    logger.debug('saving session...')
    request.session['storage_devicefile'] = device['devicefile']
    request.session['storage_label'] = device['label']
    request.session['storage_mount_path'] = device['mountpath']
    logger.debug('storage_devicefile: %s' % request.session['storage_devicefile'])
    logger.debug('storage_label     : %s' % request.session['storage_label'])
    logger.debug('storage_mount_path: %s' % request.session['storage_mount_path'])
    # write mount_path to cache
    logger.debug('caching base_path')
    bp = base_path(request)
    # update elasticsearch alias
    docstore.Docstore().set_alias(device['label'])
    # remove disk space data from cache
    cache.delete(DISK_SPACE_CACHE_KEY)

def mount_usb( request, device ):
    """Mounts requested device, adds /var/www/ddr/media symlink, gives feedback.
    """
    logger.debug('mount_usb(devicefile=%s, label=%s)' % (device['devicefile'], device['label']))
    logger.debug('device: %s' % device)
    mount_path = ddrstorage.mount(device['devicefile'], device['label'])
    logger.debug('mount_path: %s' % mount_path)
    if mount_path:
        ddrstorage.unlink()
        if device.get('mountpath'):
            ddrstorage.link(device['mountpath'])
            _mount_common(request, device['devicefile'], device['label'], device['mountpath'])
            msg = STORAGE_MESSAGES['MOUNT_SUCCESS'].format(device['label'])
            messages.success(request, msg)
    elif mount_path == False:
        msg = STORAGE_MESSAGES['MOUNT_FAIL_PATH'].format(
            device['devicefile'], device['label'], stat, mount_path)
        messages.warning(request, msg)
    else:
        msg = STORAGE_MESSAGES['MOUNT_FAIL'].format(
            device['devicefile'], device['label'], stat, mount_path)
        messages.error(request, msg)
    return mount_path

def mount_hdd( request, device ):
    """
    @param request: Django request object; used to access session.
    @param mount_path: Absolute path to mounted device; "/ddr" will be appended.
    """
    logger.debug('mount_hdd(%s, %s)' % (device['mountpath'], device['label']))
    logger.debug('device: %s' % device)
    ddrstorage.unlink()
    ddrstorage.link(device['mountpath'])
    _mount_common(request, device['devicefile'], device['label'], device['mountpath'])
    MB = settings.MEDIA_BASE
    if os.path.exists(MB) and os.path.islink(MB) and os.access(MB,os.W_OK):
        messages.success(request, '<strong>%s</strong> is now the active device.' % device['mountpath'])
    else:
        messages.error(request, 'Could not make <strong>%s</strong> the active device.' % device['mountpath'])
    return device['mountpath']

def _unmount_common(request):
    # remove label,mount_path from session,
    # regardless of whether unmount worked
    def _session_rm(request, key):
        if request.session.get(key, None):
            del request.session[key]
    _session_rm(request, 'storage_devicefile')
    _session_rm(request, 'storage_label')
    _session_rm(request, 'storage_mount_path')
    # remove space data from cache
    cache.delete(DISK_SPACE_CACHE_KEY)
    
def unmount_usb(request, device):
    """Removes /var/www/ddr/media symlink, unmounts requested device, gives feedback.
    
    @param request: Django request object; used to access session.
    @param device: dict containing device info. See DDR.storage.devices.
    """
    logger.debug('unmount(%s, %s)' % (device['devicefile'], device['label']))
    unmounted = ddrstorage.umount(device['devicefile'])
    logger.debug('unmounted: %s' % unmounted)
    ddrstorage.unlink()
    _unmount_common(request)
    if unmounted:
        msg = STORAGE_MESSAGES['UNMOUNT_SUCCESS'].format(device['label'])
        messages.success(request, msg)
    elif unmounted == False:
        msg = STORAGE_MESSAGES['UNMOUNT_FAIL_1'].format(
            device['devicefile'], device['label'], stat, mounted)
        messages.warning(request, msg)
    else:
        msg = STORAGE_MESSAGES['UNMOUNT_FAIL'].format(
            devicefile, label, stat, mounted)
        messages.error(request, msg)
    return unmounted

def unmount(request, devicetype, devicefile):
    device = None
    for d in devices():
        if d['devicefile'] == devicefile:
            device = d
    if not device:
        raise Exception('Device %s not in list of devices' % devicefile)
    
    if device['devicetype'] == 'hdd':
        assert False
    
    elif device['devicetype'] == 'usb':
        unmount_usb(request, device)
        return 'ok', 'unmounted'

def mount(request, devicetype, devicefile):
    device = None
    for d in devices():
        if d['devicefile'] == devicefile:
            device = d
    if not device:
        raise Exception('Device %s not in list of devices' % devicefile)
    
    if device['devicetype'] == 'hdd':
        return 0,mount_hdd(request, device)
    
    elif device['devicetype'] == 'usb':
        return 0,mount_usb(request, device)

def link(request, devicetype, basepath):
    device = None
    for d in devices():
        if d.get('basepath') == basepath:
            device = d
    if not device:
        raise Exception('No device with basepath %s.' % basepath)
    
    ddrstorage.unlink()
    ddrstorage.link(device['basepath'])
    _mount_common(request, device)

    if os.path.exists(settings.MEDIA_BASE):
        return 'ok','Device %s has been linked.' % device['label']
    return 'err','Device %s could not be linked.' % device['label']

def unlink(request, devicetype, basepath):
    device = None
    for d in devices():
        if d.get('basepath') == basepath:
            device = d
    if not device:
        raise Exception('No device with basepath %s.' % basepath)
    
    ddrstorage.unlink()
    _unmount_common(request)
    
    if os.path.exists(settings.MEDIA_BASE):
        return 'err','Device %s could not be unlinked.' % device['label']
    return 'ok','Device %s has been unlinked.' % device['label']
