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
import getpass
import json
import logging
import os
import sys

from DDR import batch
from DDR import idservice
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
    
    @param csv_path: Absolute path to CSV file.
    @param collection_path: Absolute path to collection repo.
    @param args_model: str 'entity' or 'file'
    @returns: model
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

def username_password(args):
    """
    @param args:
    """
    if args.username:
        username = args.username
    else:
        username = args.user
    if args.password:
        password = args.password
    else:
        password = getpass.getpass(prompt='Password: ')
    return username,password

def get_entity_ids(collection_id, session):
    """
    TODO do we actually need to log in?
    
    @param collection_id: str
    @param session: requests.session.Session object
    """
    logging.debug('Getting entity IDs')
    repo,org,cid = collection_id.split('-')
    return idservice.entities_latest(session, repo,org,cid, -1)

def register_ids(added, collection_id, session):
    """Register the specified entity IDs with the ID service
    
    @param added: list of Entity objects
    @param collection_id: str
    @param session: requests.session.Session object
    """
    logging.debug('Registering new entity IDs')
    idservice.register_entity_ids(session, added)

def confirm_added(expected, collection_id, session):
    """Confirm that entity_ids were added.
    
    @param expected: list of entities
    @param collection_id: str
    @param session: requests.session.Session object
    @returns: list of entity_ids NOT added
    """
    logging.debug('Confirming that entity IDs were added')
    entity_ids = get_entity_ids(collection_id, session)
    confirmed = [entity.id for entity in expected if entity.id in entity_ids]
    return confirmed


def main():

    parser = argparse.ArgumentParser(description=description, epilog=epilog,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('csv', help='Absolute path to CSV file.')
    parser.add_argument('collection', help='Absolute path to Collection.')
    parser.add_argument('-u', '--user', required=True, help='Git user name')
    parser.add_argument('-m', '--mail', required=True, help='Git user e-mail address')
    parser.add_argument('-M', '--model', help="Model: 'entity' or 'file'.")
    parser.add_argument('-U', '--username', help='ID service username if different from Git user name.')
    parser.add_argument('-P', '--password', help='ID service pasword. If not given here, you will be prompted.')
    args = parser.parse_args()
    
    # check args
    if not os.path.exists(args.csv):
        raise Exception('ddr-export: CSV file does not exist.')
    if not (os.path.isfile(args.csv) and os.path.isdir(args.collection)):
        raise Exception('ddr-export: CSV filename comes before collection.')
    if not os.path.exists(args.collection):
        raise Exception('ddr-export: Collection does not exist.')
    
    model,class_,module = model_class_module(args.csv, args.collection, args.model)
    
    start = datetime.now()
    if model == 'entity':
        
        collection_id = os.path.basename(args.collection)
        username,password = username_password(args)
        session = idservice.login(username, password)

        # Check max IDs before and after
        max_eid_before = get_entity_ids(collection_id, session)[-1]
        # Update the collection repo
        updated = batch.update_entities(
            args.csv,
            args.collection,
            DDRLocalEntity, entitymodule, VOCABS_PATH,
            args.user, args.mail, 'ddr-import'
        )
        max_eid_after = get_entity_ids(collection_id, session)[-1]
        # Quit if someone else added entity IDs on the workbench
        if not (max_eid_before == max_eid_after):
            raise Exception('Entity IDs were requested during operation.')

        # See if any new entities were added
        added = []
        while updated:
            entity = updated.pop(0)
            if entity.new:
                added.append(entity)
        if added:
            logging.info('New entities were created:')
            for entity in added:
                logging.info('| %s' % entity.id)
            added_ids = [entity.id for entity in added]
            confirmed_ids = []

            # Register new entity IDs with ID service
            register = raw_input('Register new IDs with ID service? [y/N] ')
            if register and (register == 'y'):
                # register and confirm
                register_ids(added, collection_id, session)
                confirmed_ids = confirm_added(added, collection_id, session)
            if confirmed_ids and (confirmed_ids == added_ids):
                logging.info('Entity IDs registered with ID service.')
            else:
                raise Exception('Some entity ids not added.')
                
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
