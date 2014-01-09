"""
import/densho
=============

These functions will
- read a properly-formatted CSV document,
- create Entities from the data,
- add the Entities to the specified Collection.
The Collection must exist on disk for this to work.


The Densho import module is part of the master branch, so switch both ddr-local and ddr-cmdln to the master branch and run the update script.::

    $ cd /usr/local/src/ddr-local/
    $ git fetch; git checkout master; git pull
    $ cd /usr/local/src/ddr-cmdln/
    $ git fetch; git checkout master; git pull
    $ cd /usr/local/src/ddr-local/ddrlocal
    $ sh bin/update.sh

Requirements:

- Properly formatted separate CSV files entities and files.  The import functions do some validation, mainly to check that file paths exist and that controlled vocabulary fields contain correct data.  The import functions will fail if files are invalid.
- The CSV files must be located in a place where they can be read from the DDR VM.  This means either in the VM itself, on a mounted USB drive, or in the VM's shared folder.
- Files to be imported must be present in the root of the folder that contains the files data CSV. 


Walkthrough - import entities
-----------------------------

Become the ddr user if you are not already.::

    $ su ddr
    [password]

Clone the collection.::

    # Excerpt from the ddr manpage:
    #     -u USER, --user USER  User name
    #     -m MAIL, --mail MAIL  User e-mail address
    #     -i CID, --cid CID     A valid DDR collection UID
    #     --dest DEST           Absolute path to which repo will be cloned (includes collection UID)
     
    $ ddr clone -u gjost -m gjost@densho.org -i ddr-densho-242 --dest /var/www/media/base/ddr-densho-242

Run the import.::

    $ ./manage.py shell
    >>> from importers import densho
    >>> csv_path = '/tmp/ddr-densho-242-entities.csv'
    >>> collection_path = '/var/www/media/base/ddr-densho-242'
    >>> git_name = 'gjost'
    >>> git_mail = 'gjost@densho.org'
    >>> densho.import_entities(csv_path, collection_path, git_name, git_mail)

Check everything.

If something didn't work quite right, remove the collection and go back to the beginning of the walkthrough to try again.::

    $ sudo rm -Rf /var/www/media/base/ddr-densho-242

Sync with mits.  NOT IMPLEMENTED YET.


Walkthrough - import files
--------------------------

The process for importing files is basically the same as above, except that it takes longer.::

    $ ./manage.py shell
    >>> from importers import densho
    >>> csv_path = '/tmp/ddr-densho-242-files.csv'
    >>> collection_path = '/var/www/media/base/ddr-densho-242'
    >>> git_name = 'gjost'
    >>> git_mail = 'gjost@densho.org'
    >>> densho.import_files(csv_path, collection_path, git_name, git_mail)

# Check everything.

Sync with mits.  NOT IMPLEMENTED YET.

"""

from __future__ import division
import csv
from datetime import datetime
import logging
logger = logging.getLogger(__name__)
import os
import sys
import doctest

from django.conf import settings

from DDR import commands
from webui.models import Collection, Entity
from ddrlocal.models import DDRLocalFile
from ddrlocal.models.entity import ENTITY_FIELDS
from ddrlocal.models.entity import STATUS_CHOICES, PERMISSIONS_CHOICES, RIGHTS_CHOICES
from ddrlocal.models.entity import LANGUAGE_CHOICES, GENRE_CHOICES, FORMAT_CHOICES
from ddrlocal.models.files import FILE_FIELDS
from webui.tasks import add_file
#def add_file( git_name, git_mail, entity, src_path, role, data ):
#    print('add_file(%s, %s, %s, %s, %s, %s)' % (git_name, git_mail, entity, src_path, role, data))


COLLECTION_FILES_PREFIX = 'files'
ENTITY_REQUIRED_FIELDS_EXCEPTIONS = ['record_created', 'record_lastmod',]
FILE_REQUIRED_FIELDS_EXCEPTIONS = ['thumb',]



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

def get_required_fields( object_class, fields ):
    """Picks out the required fields.
    @param fields: COLLECTION_FIELDS, ENTITY_FIELDS, FILE_FIELDS
    @return list of field names
    """
    if object_class == 'entity': exceptions = ENTITY_REQUIRED_FIELDS_EXCEPTIONS
    elif object_class == 'file': exceptions = FILE_REQUIRED_FIELDS_EXCEPTIONS
    required_fields = []
    for field in fields:
        if field.get('form', None) and field['form']['required'] and (field['name'] not in exceptions):
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

def valid_choice_values( choices ):
    """
    @param choices: List of value:descriptor tuples from MODEL_FIELDS doc.
    @returns list of values
    """
    return [value for value,descriptor in choices]

STATUS_CHOICES_VALUES = valid_choice_values(STATUS_CHOICES)
PUBLIC_CHOICES_VALUES = valid_choice_values(PERMISSIONS_CHOICES)
RIGHTS_CHOICES_VALUES = valid_choice_values(RIGHTS_CHOICES)
LANGUAGE_CHOICES_VALUES = valid_choice_values(LANGUAGE_CHOICES)
GENRE_CHOICES_VALUES = valid_choice_values(GENRE_CHOICES)
FORMAT_CHOICES_VALUES = valid_choice_values(FORMAT_CHOICES)

def choice_is_valid( valid_choices, choice ):
    """Indicates whether choice is valid for CHOICES
    
    @param choices: List of valid choice values.
    @param choice: A particular choice value.
    @returns True for good, False for bad
    """
    if choice in valid_choices:
        return True
    return False

def invalid_values( object_class, headers, rowd ):
    """
    @param headers: List of field names
    @param rowd: A single row (dict, not list of fields)
    @returns False (nothing missing) or a list of fieldnames
    """
    invalid = []
    if object_class == 'entity':
        if not choice_is_valid(STATUS_CHOICES_VALUES, rowd['status']): invalid.append('status')
        if not choice_is_valid(PUBLIC_CHOICES_VALUES, rowd['public']): invalid.append('public')
        if not choice_is_valid(RIGHTS_CHOICES_VALUES, rowd['rights']): invalid.append('rights')
        if not choice_is_valid(LANGUAGE_CHOICES_VALUES, rowd['language']): invalid.append('language')
        if not choice_is_valid(GENRE_CHOICES_VALUES, rowd['genre']): invalid.append('genre')
        if not choice_is_valid(FORMAT_CHOICES_VALUES, rowd['format']): invalid.append('format')
    elif object_class == 'file':
        if not choice_is_valid(PUBLIC_CHOICES_VALUES, rowd['public']): invalid.append('public')
        if not choice_is_valid(RIGHTS_CHOICES_VALUES, rowd['rights']): invalid.append('rights')
    return invalid

def all_rows_valid( object_class, headers, required_fields, rows ):
    """
    @param headers: List of field names
    @param required_fields: List of required field names
    @param rows: List of rows (each with list of fields, not dict)
    @returns list of invalid rows
    """
    rows_bad = []
    for row in rows:
        rowd = make_row_dict(headers, row)
        missing_required_fields = row_missing_required_fields(required_fields, rowd)
        invalid = invalid_values(object_class, headers, rowd)
        if missing_required_fields or invalid:
            rows_bad.append(row)
        # feedback
        if missing_required_fields or invalid:
            print('INVALID ROW')
            print(row)
            if missing_required_fields:
                print('    MISSING REQUIRED FIELDS: %s' % missing_required_fields)
            if invalid:
                print('    INVALID VALUES: %s' % invalid)
            print('')
    return rows_bad

def humanize_bytes(bytes, precision=1):
    """Return a humanized string representation of a number of bytes.

    Assumes `from __future__ import division`.

    >>> humanize_bytes(1)
    '1 byte'
    >>> humanize_bytes(1024)
    '1.0 kB'
    >>> humanize_bytes(1024*123)
    '123.0 kB'
    >>> humanize_bytes(1024*12342)
    '12.1 MB'
    >>> humanize_bytes(1024*12342,2)
    '12.05 MB'
    >>> humanize_bytes(1024*1234,2)
    '1.21 MB'
    >>> humanize_bytes(1024*1234*1111,2)
    '1.31 GB'
    >>> humanize_bytes(1024*1234*1111,1)
    '1.3 GB'
    
    source: http://code.activestate.com/recipes/577081-humanized-representation-of-a-number-of-bytes/
    """
    abbrevs = (
        (1<<50L, 'PB'),
        (1<<40L, 'TB'),
        (1<<30L, 'GB'),
        (1<<20L, 'MB'),
        (1<<10L, 'kB'),
        (1, 'bytes')
    )
    if bytes == 1:
        return '1 byte'
    for factor, suffix in abbrevs:
        if bytes >= factor:
            break
    return '%.*f %s' % (precision, bytes / factor, suffix)


# import collections ---------------------------------------------------

def import_collections():
    """NOT IMPLEMENTED YET
    """
    pass


# import entities ------------------------------------------------------

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
    required_fields = get_required_fields('entity', ENTITY_FIELDS)
    # validate metadata before attempting import
    invalid_rows = all_rows_valid('entity', headers, required_fields, rows)
    if invalid_rows:
        print('FILE CONTAINS INVALID ROWS - IMPORT CANCELLED')
    else:
        collection = Collection.from_json(collection_path)
        print(collection)
        
        def prep_creators( data ): return [x.strip() for x in data.strip().split(';') if x]
        def prep_language( data ):
            if ':' in data:
                lang = data.strip().split(':')[0]
            else:
                lang = data
            return lang
        def prep_topics( data ): return [x.strip() for x in data.strip().split(';') if x]
        def prep_persons( data ): return [x.strip() for x in data.strip().split(';') if x]
        
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
                if key == 'creators': data = prep_creators(data)
                if key == 'language': data = prep_language(data)
                if key == 'topics': data = prep_topics(data)
                if key == 'persons': data = prep_persons(data)
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

def import_files( csv_path, collection_path, git_name, git_mail ):
    """
    @param csv_path: Absolute path to CSV data file.
    @param collection_path: Absolute path to collection repo.
    @param git_name: Username for use in changelog, git log
    @param git_mail: User email address for use in changelog, git log
    """
    csv_dir = os.path.dirname(csv_path)
    rows = read_csv(csv_path)
    headers = rows[0]
    rows = rows[1:]
    required_fields = get_required_fields('file', FILE_FIELDS)
    # validate metadata before attempting import
    invalid_rows = all_rows_valid('file', headers, required_fields, rows)
    if invalid_rows:
        print('FILE CONTAINS INVALID ROWS - IMPORT CANCELLED')
    else:
        collection = Collection.from_json(collection_path)
        print(collection)
        
        #def prep_creators( data ): return [x.strip() for x in data.strip().split(';') if x]
        
        # check for missing files
        # if any Entities are missing this will error out
        missing_files = []
        for row in rows:
            rowd = make_row_dict(headers, row)
            entity_id = rowd.pop('entity_id')
            repo,org,cid,eid = entity_id.split('-')
            entity_path = Entity.entity_path(None, repo, org, cid, eid)
            entity = Entity.from_json(entity_path)
            src_path = os.path.join(csv_dir, rowd.pop('file'))
            if not os.path.exists(src_path):
                missing_files.append(src_path)
        if missing_files:
            print('ONE OR MORE SOURCE FILES ARE MISSING! - IMPORT CANCELLED!')
            for f in missing_files:
                print('    %s' % f)
        # files are all accounted for, let's import
        else:
            print('Data file looks ok and files are present')
            print('')
            for row in rows:
                rowd = make_row_dict(headers, row)
                entity_id = rowd.pop('entity_id')
                repo,org,cid,eid = entity_id.split('-')
                entity_path = Entity.entity_path(None, repo, org, cid, eid)
                entity = Entity.from_json(entity_path)
                src_path = os.path.join(csv_dir, rowd.pop('file'))
                print(entity.id)
                print('%s (%s)' % (src_path, humanize_bytes(os.path.getsize(src_path))))
                role = rowd.pop('role')
                started = datetime.now()
                print('%s importing' % started)
                #print('add_file(%s, %s, %s, %s, %s, %s)' % (git_name, git_mail, entity, src_path, role, rowd))
                add_file( git_name, git_mail, entity, src_path, role, rowd )
                finished = datetime.now()
                elapsed = finished - started
                print('%s done' % (finished))
                print('')
