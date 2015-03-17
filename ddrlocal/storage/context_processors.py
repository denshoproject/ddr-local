"""
See http://www.b-list.org/weblog/2006/jun/14/django-tips-template-context-processors/
"""
from django.conf import settings

import storage


STORAGE_WARNING_THRESHOLD = 80
STORAGE_DANGER_THRESHOLD = 90
STORAGE_DANGER_WARNING = 'WARNING! Disk usage at %s%%!'

BOOTSTRAP_COLORS = {
    'red': 'btn-danger',
    'yellow': 'btn-warning',
    'green': 'btn-success',
    'unknown': '',
}

STORAGE_TYPE_LABEL = {
    'unknown': 'label-warning',
    'known': 'label-info',
}

def sitewide(request):
    """Variables that need to be inserted into all templates.
    """
    #label = storage.drive_label(mount_path)
    #mount_path = storage.base_path(request)
    label = request.session.get('storage_label', None)
    mount_path = request.session.get('storage_mount_path', None)
    store = {
        'path': '???',
        'type': storage.storage_type(mount_path),
        'disk_label': 'no storage',
        'more_info': '',
        'disk_space': '',
        'status': '',
        'type_label': BOOTSTRAP_COLORS['red'],
        'space_label': BOOTSTRAP_COLORS['red'],
        'status_label': BOOTSTRAP_COLORS['red'],
    }
    if label:
        store['disk_label'] = label
        store['type_label'] = BOOTSTRAP_COLORS['green']
    # status
    status = 'unknown'
    if mount_path:
        status = storage.status(mount_path)
        store['status'] = status
    if status == 'ok':
        store['status_label'] = BOOTSTRAP_COLORS['green']
    # space
    space = storage.disk_space(mount_path)
    if space:
        for key,val in space.iteritems():
            store[key] = val
        # nicely formatted
        store['disk_space'] = '{} used ({}%) {} free'.format(
            store['used'], store['percent'], store['avail']
        )
        # color of disk space pill
        percent = int(space.get('percent', 0))
        if percent:
            if   percent <= STORAGE_WARNING_THRESHOLD:
                store['space_label'] = BOOTSTRAP_COLORS['green']
            elif percent <= STORAGE_DANGER_THRESHOLD:
                store['type_label'] = BOOTSTRAP_COLORS['yellow']
                store['space_label'] = BOOTSTRAP_COLORS['yellow']
                store['status_label'] = BOOTSTRAP_COLORS['yellow']
            else:
                store['type_label'] = BOOTSTRAP_COLORS['red']
                store['space_label'] = BOOTSTRAP_COLORS['red']
                store['status_label'] = BOOTSTRAP_COLORS['red']
                store['disk_full_warning'] = STORAGE_DANGER_WARNING % (percent)
    return {
        'storage': store,
    }
