"""
import_densho
=============

This script will
- read a properly-formatted CSV document,
- create Entities from the data,
- add the Entities to the specified Collection.
The Collection must exist on disk for this to work.


Walkthrough
-----------

Log in to VM
$ cd /usr/local/src/ddr-local/ddrlocal

# Remove existing collection if something didn't work just right
$ sudo rm -Rf /var/www/media/base/ddr-densho-242

# Become ddr
$ su ddr
[password]

# If you don't already have the collection, clone it
# You may want to do this each 
#     -u USER, --user USER  User name
#     -m MAIL, --mail MAIL  User e-mail address
#     -i CID, --cid CID     A valid DDR collection UID
#     --dest DEST           Absolute path to which repo will be cloned (includes collection UID)
$ ddr clone -u gjost -m gjost@densho.org -i ddr-densho-242 --dest /var/www/media/base/ddr-densho-242

# Run the import
$ ./manage.py shell
>>> from importers import densho
>>> csv_path = '/tmp/ddr-densho-242-entities.csv'
>>> collection_path = '/var/www/media/base/ddr-densho-242'
>>> git_name = 'gjost'
>>> git_mail = 'gjost@densho.org'
>>> densho.import_entities(csv_path, collection_path, git_name, git_mail)

# Check everything.

# Sync with mits

"""

import csv
from datetime import datetime
import os
import sys

from django.conf import settings

from DDR import commands
from webui.models import Collection, Entity
from ddrlocal.models.entity import ENTITY_FIELDS

COLLECTION_FILES_PREFIX = 'files'
REQUIRED_FIELDS_EXCEPTIONS = ['record_created', 'record_lastmod', 'status', 'rights']


# helper functions -----------------------------------------------------

def read_csv( path ):
    """
    @param path: Absolute path to CSV file
    @returns list of rows
    """
    rows = []
    with open(path, 'rU') as f:  # the 'U' is for universal-newline mode
        reader = csv.reader(f, delimiter=',', quoting=csv.QUOTE_ALL)
        for row in reader:
            rows.append(row)
    return rows

def get_required_fields( fields ):
    """Picks out the required fields.
    @param fields: COLLECTION_FIELDS, ENTITY_FIELDS, FILE_FIELDS
    @return list of field names
    """
    required_fields = []
    for field in fields:
        if field.get('form', None) \
           and field['form']['required'] \
           and (field['name'] not in REQUIRED_FIELDS_EXCEPTIONS):
            required_fields.append(field['name'])
    return required_fields

def make_row_dict( headers, row ):
    """Turns the row into a dict with the headers as keys
    
    @param headers: List of header field names
    @param row: A single row (list of fields, not dict)
    @returns dict
    """
    if len(headers) != len(row):
        raise Exception
    d = {}
    for n in range(0, len(row)):
        d[headers[n]] = row[n]
    return d

def row_missing_required_fields( required_fields, row ):
    """
    @param required_fields: List of required field names
    @param row: A single row (list of fields, not dict)
    @returns False (nothing missing) or a list of fieldnames
    """
    present = []
    for key in row.keys():
        if (key in required_fields) and row[key]:
            present.append(key)
    if len(present) == len(required_fields):
        return False
    missing = [x for x in required_fields if x not in present]
    return missing

def all_rows_valid( headers, required_fields, rows ):
    """
    @param headers: List of field names
    @param required_fields: List of required field names
    @param rows: List of rows (each with list of fields, not dict)
    @returns list of invalid rows
    """
    rows_bad = []
    for row in rows:
        rowd = make_row_dict(headers, row)
        if row_missing_required_fields(required_fields, rowd):
            rows_bad.append(row)
    return rows_bad



# import collections ---------------------------------------------------

def import_collections():
    """NOT IMPLEMENTED YET
    """
    pass



# import entities ------------------------------------------------------

def prep_entity_creators( data ): return [x.strip() for x in data.strip().split(';') if x]
def prep_entity_language( data ):
    if ':' in data:
        lang = data.strip().split(':')[0]
    else:
        lang = data
    return lang
def prep_entity_topics( data ): return [x.strip() for x in data.strip().split(';') if x]
def prep_entity_persons( data ): return [x.strip() for x in data.strip().split(';') if x]

def import_entities( csv_path, collection_path, git_name, git_mail ):
    """
    @param csv_path: Absolute path to CSV data file.
    @param collection_path: Absolute path to collection repo.
    @param git_name: Username for use in changelog, git log
    @param git_mail: User email address for use in changelog, git log
    """
    rows = read_csv(csv_path)
    headers = rows[0]
    rows = rows[1:]
    required_fields = get_required_fields(ENTITY_FIELDS)
    invalid_rows = all_rows_valid(headers, required_fields, rows)
    if invalid_rows:
        print('some rows not valid:')
        for row in invalid_rows:
            print(row)
    else:
        collection = Collection.from_json(collection_path)
        print(collection)
        for row in rows:
            rowd = make_row_dict(headers, row)
            
            # create new entity
            entity_uid = rowd['id']
            entity_path = os.path.join(collection_path, COLLECTION_FILES_PREFIX, entity_uid)
            
            # write entity.json template to entity location
            Entity(entity_path).dump_json(path=settings.TEMPLATE_EJSON, template=True)
            # commit files
            exit,status = commands.entity_create(git_name, git_mail,
                                                 collection.path, entity_uid,
                                                 [collection.json_path_rel, collection.ead_path_rel],
                                                 [settings.TEMPLATE_EJSON, settings.TEMPLATE_METS])
            
            # reload newly-created Entity object
            entity = Entity.from_json(entity_path)
            
            # insert values from CSV
            for key in rowd.keys():
                data = rowd[key]
                if key == 'creators': data = prep_entity_creators(data)
                if key == 'language': data = prep_entity_language(data)
                if key == 'topics': data = prep_entity_topics(data)
                if key == 'persons': data = prep_entity_persons(data)
                setattr(entity, key, data)
            entity.record_created = datetime.now()
            entity.record_lastmod = datetime.now()
            
            # write back to file
            entity.dump_json()
            updated_files = [entity.json_path]
            exit,status = commands.entity_update(git_name, git_mail,
                                                 entity.parent_path, entity.id,
                                                 updated_files)
            
            print(entity)



# import files ---------------------------------------------------------

def import_files():
    """NOT IMPLEMENTED YET
    """
    pass
