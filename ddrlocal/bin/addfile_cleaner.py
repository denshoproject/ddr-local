#!/usr/bin/env python
#
# This file is part of ddr-local
#
#

description = """Moves a collection's addfile.logs out to a common log directory."""

epilog = """
See also ddrlocal.models.Entity._addfile_log_path.

/STORE/log/REPO-ORG-CID/REPO-ORG-CID-EID-addfile.log
/STORE/log/REPO-ORG-CID.tgz
"""

from datetime import datetime
import argparse
import os
import shutil

import envoy


def find_logfiles( collection_path ):
    os.chdir(collection_path)
    CMD = 'git status -s'
    r = envoy.run(CMD)
    if r.status_code:
        assert False
    paths = []
    for line in r.std_out.split('\n'):
        if ('??' in line) and ('addfile.log' in line):
            status,relpath = line.split(' ', 1)
            path = os.path.join(collection_path, relpath)
            paths.append(path)
    return paths


def main():

    parser = argparse.ArgumentParser(description=description, epilog=epilog,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-c', '--collection', required=True, help='Absolute path to source collection repository.')
    parser.add_argument('-d', '--debug', action='store_true', help="Don't change anything, just list files that would be changed.")
    parser.add_argument('-m', '--move', action='store_true', help="Don't just copy logfiles, move them to new dir.")
    parser.add_argument('-r', '--rmtmp', action='store_true', help="Remove raw logfiles after finishing tgz.")
    
    args = parser.parse_args()
    collection_path = os.path.realpath(args.collection)
    debug = args.debug
    if args.move:
        cpmv = 'mv'
    else:
        cpmv = 'cp'
    
    
    media_base = os.path.dirname(collection_path)
    collection_id = os.path.basename(collection_path)
    logs_dir = os.path.join(media_base, 'log')
    dest_dir = os.path.join(media_base, 'log', '%s-addfiles' % collection_id)
    tgz_path = os.path.join('%s.tgz' % dest_dir)
    print('media_base %s' % media_base)
    print('dest_dir %s' % dest_dir)
    print('tgz_path %s' % tgz_path)
    
    if not os.path.exists(dest_dir):
        print('making dest dir %s' % dest_dir)
        if not debug:
            os.makedirs(dest_dir)
    
    # copy files
    print('copying...')
    logfiles = find_logfiles(collection_path)
    for logpath in logfiles:
        entity_id = os.path.basename(os.path.dirname(logpath))
        dest = os.path.join(dest_dir, '%s.log' % entity_id)
        cmd = '%s %s %s' % (cpmv, logpath, dest)
        print(cmd)
        if not debug:
            r = envoy.run(cmd)
    
    # tgz
    print('compressing...')
    os.chdir(logs_dir)
    TAR_CMD = 'tar czvf %s %s' % (os.path.basename(tgz_path), os.path.basename(dest_dir))
    print(TAR_CMD)
    if not debug:
        r = envoy.run(TAR_CMD)
        print(r.std_out.strip())
    print('-> %s' % tgz_path)
    
    if args.rmtmp:
        print('removing temp files %s' % dest_dir)
        if not debug:
            shutil.rmtree(dest_dir)

if __name__ == '__main__':
    main()
