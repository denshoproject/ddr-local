"""
See http://www.b-list.org/weblog/2006/jun/14/django-tips-template-context-processors/
"""
from django.conf import settings

from DDR import storage

def sitewide(request):
    """Variables that need to be inserted into all templates.
    """
    mountpoint = storage.mount_point(settings.DDR_BASE_PATH)
    stype = storage.storage_type(settings.DDR_BASE_PATH)
    sstatus = storage.storage_status(settings.DDR_BASE_PATH)
    return {
        'storage_root': settings.DDR_BASE_PATH,
        'storage_type': stype,
        'storage_status': sstatus,
    }
