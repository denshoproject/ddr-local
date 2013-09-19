import logging
logger = logging.getLogger(__name__)
import os

import envoy

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache

from DDR import commands


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


def base_path(request=None):
    """The actual base path to the Repository; includes USB device name.
    
    We don't know this in advance.
    We also don't want the user to have to edit a settings file in order
    to use a different device.
    
    MEDIA_ROOT, which is used by the rest of the application and by
    the www server, uses the symlink managed by add_media_symlink() and
    rm_media_symlink().
    """
    key = 'ddrlocal:base_path'
    path = cache.get(key)
    if path and (path != BASE_PATH_DEFAULT):
        # expires %{BASE_PATH_TIMEOUT} after last access
        cache.set(key, path, BASE_PATH_TIMEOUT)
        return path
    else:
        mount_path = None
        path = BASE_PATH_DEFAULT
        if request:
            mount_path = request.session.get('storage_mount_path', None)
        if mount_path:
            path = os.path.join(mount_path, settings.DDR_USBHDD_BASE_DIR)
            cache.set(key, path, BASE_PATH_TIMEOUT)
    return path

def media_base_target():
    """Returns current target of MEDIA_BASE or None if not set.
    
    If the path you provide to os.path.realpath is missing realpath will return
    the path you give it.  If the symlink is missing we need to indicate that.
    """
    if os.path.exists(settings.MEDIA_BASE):
        return os.path.realpath(settings.MEDIA_BASE)
    return None

def disk_space(mount_path):
    """Returns disk space info for the mounted drive.
    
    Uses 'df -h' on the back-end.
        Filesystem  Size  Used  Avail  Use%  Mounted on
    TODO Make this work on drives with spaces in their name!
    """
    fs = None
    r = envoy.run('df -h')
    for line in r.std_out.strip().split('\n'):
        while line.find('  ') > -1:
            line = line.replace('  ', ' ')
        parts = line.split(' ')
        path = parts[5]
        if (path in mount_path) and (path != '/'):
            fs = {'size': parts[1],
                  'used': parts[2],
                  'total': parts[3],
                  'percent': parts[4].replace('%',''),
                  'mount': parts[5],}
    return fs

def add_media_symlink(base_path):
    """Creates symlink to base_path in /var/www/media/

    We don't know the USB HDD name in advance, so we can't specify a path
    to the real media directory in the nginx config.  This func adds a symlink
    from /var/www/media/ to the ddr/ directory of the USB HDD.
    """
    target = base_path
    link = settings.MEDIA_BASE
    link_parent = os.path.split(link)[0]
    s = []
    if os.path.exists(target):          s.append('1')
    else:                               s.append('0')
    if os.path.exists(link_parent):     s.append('1')
    else:                               s.append('0')
    if os.access(link_parent, os.W_OK): s.append('1')
    else:                               s.append('0')
    s = ''.join(s)
    if s == '111':
        os.symlink(target, link)

def rm_media_symlink(base_path):
    """Remove the media symlink (see add_media_symlink).
    """
    link = settings.MEDIA_BASE
    s = []
    if os.path.exists(link):     s.append('1') 
    else:                        s.append('0')
    if os.path.islink(link):     s.append('1') 
    else:                        s.append('0')
    if os.access(link, os.W_OK): s.append('1') 
    else:                        s.append('0')
    if ''.join(s) == '111':
        os.remove(link)

def mount( request, devicefile, label ):
    """Mounts requested device, adds /var/www/ddr/media symlink, gives feedback.
    """
    logger.debug('mount(%s, %s)' % (devicefile, label))
    if not (devicefile and label):
        messages.error(request, STORAGE_MESSAGES['MOUNT_ERR_MISSING_INFO'].format(devicefile, label))
        return None
    stat,mount_path = commands.mount(devicefile, label)
    logger.debug('stat: %s' % stat)
    logger.debug('mount_path: %s' % mount_path)
    if mount_path:
        messages.success(request, STORAGE_MESSAGES['MOUNT_SUCCESS'].format(label))
        rm_media_symlink(base_path())
        add_media_symlink(base_path())
        # save label,mount_path in session
        request.session['storage_devicefile'] = devicefile
        request.session['storage_label'] = label
        request.session['storage_mount_path'] = mount_path
        # write mount_path to cache
        bp = base_path(request)
    elif mount_path == False:
        messages.warning(request, STORAGE_MESSAGES['MOUNT_FAIL_PATH'].format(devicefile, label, stat, mount_path))
    else:
        messages.error(request, STORAGE_MESSAGES['MOUNT_FAIL'].format(devicefile, label, stat, mount_path))
    return mount_path

def unmount( request, devicefile, label ):
    """Removes /var/www/ddr/media symlink, unmounts requested device, gives feedback.
    """
    logger.debug('unmount(%s, %s)' % (devicefile, label))
    unmounted = None
    if devicefile:
        rm_media_symlink(base_path())
        stat,unmounted = commands.umount(devicefile)
        logger.debug('stat: %s' % stat)
        logger.debug('unmounted: %s' % unmounted)
        # remove label,mount_path from session,
        # regardless of whether unmount worked
        try:
            del request.session['storage_devicefile']
            del request.session['storage_label']
            del request.session['storage_mount_path']
        except KeyError:
            pass
    if unmounted:
        messages.success(request, STORAGE_MESSAGES['UNMOUNT_SUCCESS'].format(label))
    elif unmounted == False:
        messages.warning(request, STORAGE_MESSAGES['UNMOUNT_FAIL_1'].format(devicefile, label, stat, mounted))
    else:
        messages.error(request, STORAGE_MESSAGES['UNMOUNT_FAIL'].format(devicefile, label, stat, mounted))
    return unmounted
