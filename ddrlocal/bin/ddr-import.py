#!/usr/bin/env python
#
# ddr-import
#
#  

description = """Imports DDR entities or files from CSV to the specified collection."""

epilog = """
"""


import argparse
import ConfigParser
from datetime import datetime
import json
import logging
import os
import sys

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
VOCABS_PATH = os.path.join(REPO_MODELS_PATH, 'vocab')

if REPO_MODELS_PATH not in sys.path:
    sys.path.append(REPO_MODELS_PATH)
try:
    from repo_models import collection as collectionmodule
    from repo_models import entity as entitymodule
    from repo_models import files as filemodule
except ImportError:
    # No Store mounted, no 'ddr' repository, or no valid repo_models in 'ddr'.
    raise Exception('Could not load repo_models.')

ENTITY_MODULE_NAMES = ['entity', 'entities']
FILE_MODULE_NAMES = ['file', 'files']
MODULE_NAMES = ENTITY_MODULE_NAMES + FILE_MODULE_NAMES


def main():

    parser = argparse.ArgumentParser(description=description, epilog=epilog,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('csv', help='Absolute path to CSV file.')
    parser.add_argument('collection', help='Absolute path to Collection.')
    parser.add_argument('-u', '--user', required=True, help='User name')
    parser.add_argument('-m', '--mail', required=True, help='User e-mail address')
    parser.add_argument('-M', '--module', required=True, help="Module: 'entity' or 'file'.")
    args = parser.parse_args()
    
    # check args
    if not os.path.exists(args.csv):
        print('ddr-export: CSV file does not exist.')
        sys.exit(1)
    if not (os.path.isfile(args.csv) and os.path.isdir(args.collection)):
        print('ddr-export: CSV filename comes before collection.')
        sys.exit(1)
    if not os.path.exists(args.collection):
        print('ddr-export: Collection does not exist.')
        sys.exit(1)
    
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
        module = filemodule

    if not (class_ and module):
        raise Exception('ERROR: Could not decide on a class/module.')
    
    start = datetime.now()
    print('%s Starting...' % start)
    
    if model == 'entity':
        updated = batch.update_entities(
            args.csv,
            args.collection,
            DDRLocalEntity, entitymodule, VOCABS_PATH,
            args.user, args.mail, 'ddr-import'
        )
    elif model == 'file':
        updated = batch.update_files(
            args.csv,
            args.collection,
            DDRLocalEntity, DDRLocalFile, module, VOCABS_PATH,
            args.user, args.mail, 'ddr-import'
        )
    
    finish = datetime.now()
    elapsed = finish - start
    print('%s done' % finish)
    print('%s elapsed' % elapsed)



if __name__ == '__main__':
    main()
