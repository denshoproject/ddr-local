#!/usr/bin/env python
#
# ddr-export
#
#  

description = """Exports a DDR collection's entities or files to CSV."""

epilog = """
Sample ID formats:
    ddr-test-123-*            All entities in a collection
    ddr-test-123-1-*          All files in an entity
    ddr-test-123-*            All files in a collection
    ddr-test-123-[1-5,7-8,10] Ranges of entities
"""


import argparse
import ConfigParser
from datetime import datetime
import json
import logging
import os
import sys

from DDR import natural_sort
from DDR import batch
from DDR import models

DDRLOCAL_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(DDRLOCAL_PATH)
from ddrlocal.models import DDRLocalCollection, DDRLocalEntity, DDRLocalFile

CONFIG_FILES = ['/etc/ddr/ddr.cfg', '/etc/ddr/local.cfg']
config = ConfigParser.ConfigParser()
configs_read = config.read(CONFIG_FILES)
if not configs_read:
    raise NoConfigError('No config file!')

REPO_MODELS_PATH = config.get('cmdln','repo_models_path')
if REPO_MODELS_PATH not in sys.path:
    sys.path.append(REPO_MODELS_PATH)
try:
    from repo_models import collection as collectionmodule
    from repo_models import entity as entitymodule
    from repo_models import files as filemodule
except ImportError:
    # No Store mounted, no 'ddr' repository, or no valid repo_models in 'ddr'.
    raise Exception('Could not load repo_models.')


ENTITY_MODULE_NAMES = ['entity', 'entities', 'file', 'files']
FILE_MODULE_NAMES = ['entity', 'entities', 'file', 'files']
MODULE_NAMES = ENTITY_MODULE_NAMES + FILE_MODULE_NAMES


def parse_ids(text):
    """Parses IDs arg and returns list of IDs.
    
    ddr-test-123-*            All entities in a collection
    ddr-test-123-1-*          All files in an entity
    ddr-test-123-*            All files in a collection
    ddr-test-123-[1-5,7-8,10] Ranges of entities
    
    TODO Seriously? Can't we just pass in a regex?
    
    @param text: str
    @returns: list
    """
    ids = []
    if ('[' in text) and (']' in text):
        f0 = text.split('[')[0]
        fids = text.split('[')[1].split(']')[0]
        fids1 = fids.split(',')
        for x in fids1:
            if '-' in x:
                lo,hi = x.split('-')
                for y in range(int(lo), int(hi)+1):
                    i = f0 + str(y)
                    ids.append(i)
            else:
                i = f0 + str(x)
                ids.append(i)
    elif '*' in text:
        fid = text
    return ids

def read_id_file(path):
    """Read file and return list of IDs
    
    @param path: str Absolute path to file.
    @returns: list of IDs
    """
    with open(path, 'r') as f:
        text = f.read()
    ids = [line.strip() for line in text.split('\n')]
    return ids


def main():

    parser = argparse.ArgumentParser(description=description, epilog=epilog,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-i', '--ids', help='ID(s) (see help for formatting).')
    parser.add_argument('-f', '--file', help='File containing list of IDs, one per line.')
    parser.add_argument('-m', '--module', required=True, help="Module: 'entity' or 'file'.")
    parser.add_argument('collection', help='Absolute path to Collection.')
    parser.add_argument('csv', help='Absolute path to CSV file.')
    args = parser.parse_args()
    
    if not (args.ids or args.file):
        raise Exception('Specify an ID pattern or a file containing IDs.')
    elif args.file and not os.path.exists(args.file):
        raise Exception('IDs file does not exist: %s' % args.file)
    elif not os.path.exists(args.collection):
        raise Exception('Collection does not exist: %s' % args.collection)
    elif not os.access(os.path.dirname(args.csv), os.W_OK):
        raise Exception('Cannot write to %s.' % args.csv)
    elif args.module not in MODULE_NAMES:
        raise Exception("Bad module name: '%s'" % args.module)
    
    model = None
    class_ = None
    module = None
    if args.module in ENTITY_MODULE_NAMES:
        model = 'entity'
        class_ = DDRLocalEntity
        module = entitymodule
    elif args.module in FILE_MODULE_NAMES:
        model = 'file'
        class_ = DDRLocalFile
        module = filesmodule
    if not (class_ and module):
        raise Exception('ERROR: Could not decide on a class/module.')
    
    ids = []
    if args.ids:
        ids = parse_ids(args.ids)
    elif args.file:
        ids = read_id_file(args.file)
#    if not ids:
#        raise Exception('ERROR: No IDs matched')
    
    start = datetime.now()
    print('%s Gathering entity paths...' % start)
    paths = [
        path for path in models.metadata_files(
            basedir=args.collection, model=model, recursive=True
        )
    ]
    if paths:
        print('%s ok %s paths' % (datetime.now(), len(paths)))
    else:
        raise Exception('ERROR: Could not find metadata paths.')
    
    print('%s Exporting' % datetime.now())
    batch.export(paths, class_, module, args.csv)
    finish = datetime.now()
    elapsed = finish - start
    print('%s done' % finish)
    print('%s elapsed' % elapsed)
    
    

if __name__ == '__main__':
    main()
