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
    device = {
        'path': '???',
        'type': 'unknown',
        'label': 'no storage',
        'more_info': '',
        'disk_space': '',
        'mounted': 0,
        'linked': 0,
        'status': '',
    }
    for d in storage.removables():
        if mount_path and d.get('mountpath',None) \
        and (d['mountpath'] == mount_path) and d['linked']:
            device = d
    device['type_label'] = BOOTSTRAP_COLORS['red']
    device['space_label'] = BOOTSTRAP_COLORS['red']
    device['status_label'] = BOOTSTRAP_COLORS['red']
    if device['mounted'] and device['linked']:
        device['type_label'] = BOOTSTRAP_COLORS['green']
        device['status_label'] = BOOTSTRAP_COLORS['green']
    # space
    space = storage.disk_space(mount_path)
    if space:
        for key,val in space.iteritems():
            device[key] = val
        # color of disk space pill
        percent = int(space.get('percent', 0))
        if percent:
            if   percent <= STORAGE_WARNING_THRESHOLD:
                device['space_label'] = BOOTSTRAP_COLORS['green']
            elif percent <= STORAGE_DANGER_THRESHOLD:
                device['type_label'] = BOOTSTRAP_COLORS['yellow']
                device['space_label'] = BOOTSTRAP_COLORS['yellow']
                device['status_label'] = BOOTSTRAP_COLORS['yellow']
            else:
                device['type_label'] = BOOTSTRAP_COLORS['red']
                device['space_label'] = BOOTSTRAP_COLORS['red']
                device['status_label'] = BOOTSTRAP_COLORS['red']
                device['disk_full_warning'] = STORAGE_DANGER_WARNING % (percent)
    return {
        'storage': device,
    }
