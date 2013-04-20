import os

import envoy

from django.conf import settings


def mount( device_file, label ):
    """Mounts specified device at the label; returns mount_path.

    TODO FIX THIS HORRIBLY UNSAFE COMMAND!!!
    """
    mount_path = None
    cmd = 'pmount -w {} {}'.format(device_file, label)
    r = envoy.run(cmd, timeout=2)
    for d in removables_mounted():
        if label in d['mountpath']:
            mount_path = d['mountpath']
    return mount_path

def umount( device_file ):
    """Unmounts device at device_file.

    TODO FIX THIS HORRIBLY UNSAFE COMMAND!!!
    """
    unmounted = False
    cmd = 'pumount {}'.format(device_file)
    r = envoy.run(cmd, timeout=2)
    in_removables = False
    for d in removables_mounted():
        if device_file in d['devicefile']:
            in_removables = True
    if not in_removables:
        unmounted = True
    return unmounted

def removables():
    """List removable drives whether or not they are attached.
    
    $ udisks --dump
    
    @returns list of dicts containing attribs of devices
    """
    d = []
    r = envoy.run('udisks --dump', timeout=2)
    sdbchunks = []
    chunks = r.std_out.split('========================================================================\n')
    # get sdb* devices (sdb1, sdb2, etc)
    for c in chunks:
        if 'sdb' in c:
            lines = c.split('\n')
            numbrs = ['0','1','2','3','4','5','6','7','8','9',]
            if lines[0][-1] in numbrs:
                sdbchunks.append(c)
    # grab the interesting data for each device
    # IMPORTANT: spaces are removed from these labels when they are assigned!!!
    interesting = ['device file', 'is read only', 'is mounted', 'mount paths', 'type', 'uuid', 'label',]
    for c in sdbchunks:
        attribs = {}
        for l in c.split('\n'):
            if ':' in l:
                k,v = l.split(':', 1)
                k = k.strip().replace(' ','')
                v = v.strip()
                if (k in interesting) and v and (not k in attribs.keys()):
                    attribs[k] = v
        d.append(attribs)
    return d

def removables_mounted():
    """List mounted and accessible removable drives.

    $ pmount
    Printing mounted removable devices:
    /dev/sdb1 on /media/WD5000BMV-2 type fuseblk (rw,nosuid,nodev,relatime,user_id=0,group_id=0,default_permissions,allow_other,blksize=4096)
    To get a short help, run pmount -h
    
    @returns list of dicts containing attribs of devices
    """
    d = []
    rdevices = removables()
    r = envoy.run('pmount', timeout=2)
    for l in r.std_out.split('\n'):
        if '/dev/' in l:
            parts = l.split(' ')
            attrs = {'devicefile':parts[0], 'mountpath':parts[2],}
            if is_writable(attrs['mountpath']):
                d.append(attrs)
    return d

def is_writable(path):
    return os.access(path, os.W_OK)

def storage_type( request ):
    return 'unknown'

def storage_status( request ):
    status = 'unknown'
    path = storage_root(request)
    if path and os.path.exists(path) and is_writable(path):
        status = 'ok'
    return status

def storage_root( request, new=None ):
    if new:
        request.session['STORAGE_ROOT'] = new
    return request.session.get('STORAGE_ROOT', None)
