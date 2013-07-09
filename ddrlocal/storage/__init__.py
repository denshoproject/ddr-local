import os

from django.conf import settings
from django.core.cache import cache

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
