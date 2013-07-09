"""
See http://www.b-list.org/weblog/2006/jun/14/django-tips-template-context-processors/
"""
from django.conf import settings

from DDR import storage

from storage import base_path


def sitewide(request):
    """Variables that need to be inserted into all templates.
    """
    storage_mount_path = base_path(request)
    stype = storage.storage_type(storage_mount_path)
    sstatus = storage.storage_status(storage_mount_path)
    return {
        'storage_root': storage_mount_path,
        'storage_type': stype,
        'storage_status': sstatus,
    }
