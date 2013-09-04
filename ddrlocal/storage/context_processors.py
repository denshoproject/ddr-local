"""
See http://www.b-list.org/weblog/2006/jun/14/django-tips-template-context-processors/
"""
from django.conf import settings

from DDR import storage

from storage import base_path, disk_space

BOOTSTRAP_COLORS = {'red': 'btn-danger',
                    'yellow': 'btn-warning',
                    'green': 'btn-success',
                    'unknown': '',}

def sitewide(request):
    """Variables that need to be inserted into all templates.
    """
    storage_mount_path = base_path(request)
    stype = storage.storage_type(storage_mount_path)
    sstatus = storage.storage_status(storage_mount_path)
    dspace = disk_space(storage_mount_path)
    # change color of disk space pill
    if dspace and dspace.get('percent',None):
        if    dspace['percent'] <= 10: dspace['label'] = BOOTSTRAP_COLORS['red']
        elif  dspace['percent'] <= 30: dspace['label'] = BOOTSTRAP_COLORS['yellow']
        else:                          dspace['label'] = BOOTSTRAP_COLORS['green']
    return {
        'storage_root': storage_mount_path,
        'storage_type': stype,
        'storage_status': sstatus,
        'storage_space': dspace,
    }
