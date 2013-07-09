import os

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache

from DDR import commands


REMOUNT_POST_REDIRECT_URL_SESSION_KEY = 'remount_redirect_uri'


BASE_PATH_TIMEOUT = 60 * 30  # 30 min
BASE_PATH_DEFAULT = '/tmp/ddr'

def base_path(request=None):
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


def mount( request, devicefile, label ):
    if not (devicefile and label):
        messages.error(request, 'storage.mount(): devicefile or label missing [{} {}]'.format(devicefile, label))
        return None
    stat,mount_path = commands.mount(devicefile, label)
    if mount_path:
        messages.success(request, 'Mounted {}'.format(label))
        # save label,mount_path in session
        request.session['storage_devicefile'] = devicefile
        request.session['storage_label'] = label
        request.session['storage_mount_path'] = mount_path
        # write mount_path to cache
        bp = base_path(request)
    elif mount_path == False:
        messages.warning(request, 'Count not mount device [{} {}: {},{}]'.format(devicefile, label, stat,mount_path))
    else:
        messages.error(request, 'Problem mounting device [{} {}: {},{}]'.format(devicefile, label, stat,mount_path))
    return mount_path

def unmount( request, devicefile, label ):
    unmounted = None
    if devicefile:
        stat,unmounted = commands.umount(devicefile)
        # remove label,mount_path from session,
        # regardless of whether unmount worked
        try:
            del request.session['storage_devicefile']
            del request.session['storage_label']
            del request.session['storage_mount_path']
        except KeyError:
            pass
    if unmounted:
        messages.success(request, 'Umounted {}'.format(label))
    elif unmounted == False:
        messages.warning(request, 'Count not unmount device [{} {}: {},{}]'.format(devicefile, label, stat,mounted))
    else:
        messages.error(request, 'Problem unmounting device [{} {}: {},{}]'.format(devicefile, label, stat,mounted))
    return unmounted
