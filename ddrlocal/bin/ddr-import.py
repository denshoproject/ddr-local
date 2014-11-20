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

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-8s %(message)s',
    stream=sys.stdout,
)

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
    raise Exception("Could not load repo_models. No Store mounted, no 'ddr' repository, or no valid repo_models in 'ddr'.")

ENTITY_MODULE_NAMES = ['entity', 'entities']
FILE_MODULE_NAMES = ['file', 'files']
MODULE_NAMES = ENTITY_MODULE_NAMES + FILE_MODULE_NAMES


def guess_model(csv_path, collection_path, args_model=None):
    """Try to guess module from csv path.
    
    Works if CSV path in the form COLLECTIONID-MODEL.csv
    e.g. ddr-test-123-entity.csv
    """
    if collection_path[-1] == os.sep:
        collection_path = collection_path[:-1]
    cid = os.path.basename(collection_path)
    try:
        model = os.path.splitext(
            os.path.basename(csv_path)
        )[0].replace(cid,'').replace('-','')
    except:
        model = None
    if model and (model in MODULE_NAMES):
        return model
    return args_model

def model_class_module(csv_path, collection_path, args_model=None):
    """Pick object class and module based on model arg.
    
    @param csv_path: Absolute path to CSV file.
    @param collection_path: Absolute path to collection repo.
    @param args_model: str 'entity' or 'file'
    @returns: model, class, module
    """
    model = guess_model(csv_path, collection_path, args_model)
    if not model:
        raise Exception('ddr-export: Could not guess model based on csv and collection. Add an -M arg.')
    class_ = None
    module = None
    if model in ENTITY_MODULE_NAMES:
        model = 'entity'
        class_ = DDRLocalEntity
        module = entitymodule
    elif model in FILE_MODULE_NAMES:
        model = 'file'
        class_ = DDRLocalFile
        module = filemodule
    if not (class_ and module):
        raise Exception('ERROR: Could not decide on a class/module.')
    return model,class_,module
    

def main():

    parser = argparse.ArgumentParser(description=description, epilog=epilog,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('csv', help='Absolute path to CSV file.')
    parser.add_argument('collection', help='Absolute path to Collection.')
    parser.add_argument('-u', '--user', required=True, help='User name')
    parser.add_argument('-m', '--mail', required=True, help='User e-mail address')
    parser.add_argument('-M', '--model', help="Model: 'entity' or 'file'.")
    args = parser.parse_args()
    
    # check args
    if not os.path.exists(args.csv):
        logging.debug('ddr-export: CSV file does not exist.')
        sys.exit(1)
    if not (os.path.isfile(args.csv) and os.path.isdir(args.collection)):
        logging.debug('ddr-export: CSV filename comes before collection.')
        sys.exit(1)
    if not os.path.exists(args.collection):
        logging.debug('ddr-export: Collection does not exist.')
        sys.exit(1)
    
    model,class_,module = model_class_module(args.csv, args.collection, args.model)
    
    start = datetime.now()
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
    logging.info('DONE - %s elapsed' % elapsed)



if __name__ == '__main__':
    main()
