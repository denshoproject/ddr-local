"""
migration/densho
================

These functions will
- read a properly-formatted CSV document,
- create Entities from the data,
- add the Entities to the specified Collection.
The Collection must exist on disk for this to work.


The Densho migration module is part of the master branch, so switch both ddr-local and ddr-cmdln to the master branch and run the update script.::

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
    >>> from migration.densho import import_entities
    >>> csv_path = '/tmp/ddr-testing-123-entities.csv'
    >>> collection_path = '/tmp/ddr-testing-123'
    >>> git_name = 'gjost'
    >>> git_mail = 'gjost@densho.org'
    >>> import_entities(csv_path, collection_path, git_name, git_mail)

Check everything.

If something didn't work quite right, remove the collection and go back to the beginning of the walkthrough to try again.::

    $ sudo rm -Rf /var/www/media/base/ddr-densho-242

Sync with mits.  NOT IMPLEMENTED YET.


Walkthrough - import files
--------------------------

The process for importing files is basically the same as above, except that it takes longer.::

    $ ./manage.py shell
    >>> from migration.densho import import_files
    >>> csv_path = '/tmp/ddr-testing-123-files.csv'
    >>> collection_path = '/tmp/ddr-testing-123'
    >>> git_name = 'gjost'
    >>> git_mail = 'gjost@densho.org'
    >>> import_files(csv_path, collection_path, git_name, git_mail)

# Check everything.

Sync with mits.  NOT IMPLEMENTED YET.


Walkthrough - export entities and files
---------------------------------------

Become the ddr user if you are not already.::

    $ su ddr
    [password]

Run the export.::

    $ ./manage.py shell
    >>> from migration.densho import export_entities, export_files
    >>> collection_path = '/tmp/ddr-testing-123'
    >>> csv_path = '/tmp/ddr-testing-123.csv'
    >>> export_entities(collection_path, csv_path)
    ...
    >>> export_files(collection_path, csv_path)
    ...


"""

from __future__ import division
from copy import deepcopy
import csv
from datetime import datetime
import json
import logging
logger = logging.getLogger(__name__)
import os
import sys
import doctest

from django.conf import settings

from DDR import commands
from DDR.models import metadata_files
from webui.models import Collection, Entity
from ddrlocal.models import module_function
from ddrlocal.models import DDRLocalEntity, DDRLocalFile
from ddrlocal.models import entity as entitymodule
from ddrlocal.models import files as filemodule
from ddrlocal.models.entity import ENTITY_FIELDS
from ddrlocal.models.entity import STATUS_CHOICES, PERMISSIONS_CHOICES, RIGHTS_CHOICES
from ddrlocal.models.entity import LANGUAGE_CHOICES, GENRE_CHOICES, FORMAT_CHOICES
from ddrlocal.models.files import FILE_FIELDS
#def add_file( git_name, git_mail, entity, src_path, role, data ):
#    print('add_file(%s, %s, %s, %s, %s, %s)' % (git_name, git_mail, entity, src_path, role, data))

AGENT = 'importers.densho'

# Some files' XMP data is wayyyyyy too big
csv.field_size_limit(sys.maxsize)
CSV_DELIMITER = ','
CSV_QUOTECHAR = '"'
CSV_QUOTING = csv.QUOTE_ALL

# These are lists of alternative forms of controlled-vocabulary terms.
# From these indexes are build that will be used to replace variant terms with the official term.
ENTITY_HEADER_FIELDS_ALT = {
    'facility': ['facilities',],
}
FILE_HEADER_FIELDS_ALT = {
    'basename_orig': ['file',],
}
STATUS_CHOICES_ALT = {
    'inprocess': ['In Process', 'In Progress', 'inprogress',],
    'completed': ['Completed', 'complete', 'Complete',],
}
PERMISSIONS_CHOICES_ALT = {
    '1': ['public', 'Public',],
    '0': ['private', 'Private',],
}
LANGUAGE_CHOICES_ALT = {
    'eng': ['english', 'English', 'eng:English',],
    'jpn': ['japanese', 'Japanese', 'jpn:Japanese',],
    'chi': ['chinese', 'Chinese', 'chi:Chinese',],
    'fre': ['french', 'French', 'fre:French',],
    'ger': ['german', 'German', 'ger:German',], 
    'ita': ['italian', 'Italian', 'ita:Italian',],
    'kor': ['korean', 'Korean', 'kor:Korean',],
    'por': ['portuguese', 'Portuguese', 'por:Portuguese',],
    'rus': ['russian', 'Russian', 'rus:Russian',],
    'spa': ['spanish', 'Spanish', 'spa:Spanish',],
    'tgl': ['tagalog', 'Tagalog', 'tgl:Tagalog',],
}
GENRE_CHOICES_ALT = {
    'advertisement': ['Advertisements', 'Advertisement',],
    'album': ['Albums', 'Album',],
    'architecture': ['Architecture',],
    'baseball_card': ['Baseball Cards', 'Baseball Card',],
    'blank_form': ['Blank Forms', 'Blank Form',],
    'book': ['Books', 'Book',],
    'broadside': ['Broadsides', 'Broadside',],
    'cartoon': ['Cartoons (Commentary)', 'Cartoon (Commentary)',],
    'catalog': ['Catalogs', 'Catalog',],
    'cityscape': ['Cityscapes', 'Cityscape',],
    'clipping': ['Clippings', 'Clipping',],
    'correspondence': ['Correspondence',],
    'diary': ['Diaries', 'Diary',],
    'drawing': ['Drawings', 'Drawing',],
    'ephemera': ['Ephemera',],
    'essay': ['Essays', 'Essay',],
    'ethnography': ['Ethnographies', 'Ethnography',],
    'fieldnotes': ['Fieldnotes', 'Fieldnote',],
    'illustration': ['Illustrations', 'Illustration',],
    'interview': ['Interviews', 'Interview',],
    'landscape': ['Landscapes', 'Landscape',],
    'leaflet': ['Leaflets', 'Leaflet',],
    'manuscript': ['Manuscripts', 'Manuscript',],
    'map': ['Maps', 'Map',],
    'misc_document': ['Miscellaneous Documents', 'Miscellaneous Document',],
    'motion_picture': ['Motion Pictures', 'Motion Picture',],
    'music': ['Music',],
    'narrative': ['Narratives', 'Narrative',],
    'painting': ['Paintings', 'Painting',],
    'pamphlet': ['Pamphlets', 'Pamphlet',],
    'periodical': ['Periodicals', 'Periodical',],
    'petition': ['Petitions', 'Petition',],
    'photograph': ['Photographs', 'Photograph',],
    'physical_object': ['Physical Objects', 'Physical Object',],
    'poetry': ['Poetry',],
    'portrait': ['Portraits', 'Portrait',],
    'postcard': ['Postcards', 'Postcard',],
    'poster': ['Posters', 'Poster',],
    'print': ['Prints', 'Print',],
    'program': ['Programs', 'Program',],
    'rec_log': ['Recording Logs', 'Recording Log',],
    'score': ['Scores', 'Score',],
    'sheet_music': ['Sheet Music',],
    'timetable': ['Timetables', 'Timetable',],
    'transcription': ['Transcriptions', 'Transcription',],
}
FORMAT_CHOICES_ALT = {
    'av': ['Audio/Visual',],
    'ds': ['Datasets', 'Dataset',],
    'doc': ['Documents', 'Document',],
    'img': ['Still Images', 'Still Image',],
    'vh': ['Oral Histories', 'Oral History',],
}

def make_choices_alt_index(choices_alt):
    """Make index from *_CHOICES_ALT dict
    """
    index = {}
    for key,value in choices_alt.iteritems():
        for v in value:
            index[v] = key
    return index
ENTITY_HEADER_FIELDS_ALT_INDEX = make_choices_alt_index(ENTITY_HEADER_FIELDS_ALT)
FILE_HEADER_FIELDS_ALT_INDEX = make_choices_alt_index(FILE_HEADER_FIELDS_ALT)
STATUS_CHOICES_ALT_INDEX = make_choices_alt_index(STATUS_CHOICES_ALT)
PERMISSIONS_CHOICES_ALT_INDEX = make_choices_alt_index(PERMISSIONS_CHOICES_ALT)
LANGUAGE_CHOICES_ALT_INDEX = make_choices_alt_index(LANGUAGE_CHOICES_ALT)
GENRE_CHOICES_ALT_INDEX = make_choices_alt_index(GENRE_CHOICES_ALT)
FORMAT_CHOICES_ALT_INDEX = make_choices_alt_index(FORMAT_CHOICES_ALT)


COLLECTION_FILES_PREFIX = 'files'

REQUIRED_FIELDS_EXCEPTIONS = {
    'entity': ['record_created', 'record_lastmod', 'files',],
    'file': ['thumb', 'sha1', 'sha256', 'md5', 'size', 'access_rel', 'xmp', 'links'],
}

FIELD_NAMES = {
    'entity': [field['name'] for field in ENTITY_FIELDS],
    'file': [field['name'] for field in FILE_FIELDS],
}


# helper functions -----------------------------------------------------

def dtfmt(dt): return dt.strftime('%Y-%m-%dT%H:%M:%S.%f')

def make_tmpdir():
    os.makedirs(settings.CSV_TMPDIR)
    
def make_csv_reader( csvfile ):
    """
    @param csvfile: A file object.
    """
    reader = csv.reader(
        csvfile,
        delimiter=CSV_DELIMITER,
        quoting=CSV_QUOTING,
        quotechar=CSV_QUOTECHAR,
    )
    return reader

def make_csv_writer( csvfile ):
    """
    @param csvfile: A file object.
    """
    writer = csv.writer(
        csvfile,
        delimiter=CSV_DELIMITER,
        quoting=CSV_QUOTING,
        quotechar=CSV_QUOTECHAR,
    )
    return writer

def read_csv( path ):
    """
    @param path: Absolute path to CSV file
    @returns list of rows
    """
    rows = []
    with open(path, 'rU') as f:  # the 'U' is for universal-newline mode
        reader = make_csv_reader(f)
        for row in reader:
            rows.append(row)
    return rows

def get_required_fields( object_class, fields ):
    """Picks out the required fields.
    @param fields: COLLECTION_FIELDS, ENTITY_FIELDS, FILE_FIELDS
    @return list of field names
    """
    exceptions = REQUIRED_FIELDS_EXCEPTIONS[object_class]
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

def invalid_headers( object_class, headers ):
    """
    @param object_class: 'entity' or 'file'
    @param headers: List of field names
    @returns True if everything's OK, False if not; prints errors to console
    """
    headers = deepcopy(headers)
    the_official_fields = FIELD_NAMES[object_class]
    exceptions = REQUIRED_FIELDS_EXCEPTIONS[object_class]
    if object_class == 'file':
        headers.remove('entity_id')
    # validate
    missing_headers = []
    for field in the_official_fields:
        if (field not in exceptions) and (field not in headers):
            missing_headers.append(field)
    bad_headers = []
    for header in headers:
        if header not in the_official_fields:
            bad_headers.append(header)
    if missing_headers:
        print('MISSING HEADER(S): %s' % missing_headers)
    if bad_headers:
        print('BAD HEADER(S): %s' % bad_headers)
    if missing_headers or bad_headers:
        return 1
    return 0

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
        # language can be 'eng', 'eng;jpn', 'eng:English', 'jpn:Japanese'
        for x in rowd['language'].strip().split(';'):
            if ':' in x:
                code = x.strip().split(':')[0]
            else:
                code = x.strip()
            if not choice_is_valid(LANGUAGE_CHOICES_VALUES, code) and 'language' not in invalid:
                invalid.append('language')
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

def test_entities( headers, rows ):
    """Test-loads Entities mentioned in rows; will crash if any are missing.
    """
    bad_entities = []
    for row in rows:
        rowd = make_row_dict(headers, row)
        entity_id = rowd.pop('entity_id')
        repo,org,cid,eid = entity_id.split('-')
        entity_path = Entity.entity_path(None, repo, org, cid, eid)
        try:
            entity = Entity.from_json(entity_path)
        except:
            entity = None
        if not entity:
            bad_entities.append(entity_id)
    return bad_entities

def find_missing_files( csv_dir, headers, rows ):
    """checks for missing files
    """
    missing_files = []
    for row in rows:
        rowd = make_row_dict(headers, row)
        src_path = os.path.join(csv_dir, rowd.pop('basename_orig'))
        if not os.path.exists(src_path):
            missing_files.append(src_path)
    return missing_files

def find_unreadable_files( csv_dir, headers, rows ):
    """checks for missing files
    """
    unreadable_files = []
    for row in rows:
        rowd = make_row_dict(headers, row)
        src_path = os.path.join(csv_dir, rowd.pop('basename_orig'))
        try:
            f = open(src_path, 'r')
            f.close()
        except:
            unreadable_files.append(src_path)
    return unreadable_files

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

def replace_variant_headers( object_class, headers ):
    """Tries to replace variant headers with official values
    """
    if   object_class == 'entity': index = ENTITY_HEADER_FIELDS_ALT_INDEX
    elif object_class == 'file': index = FILE_HEADER_FIELDS_ALT_INDEX
    for header in headers:
        # if value appears in index, it is a variant
        if index.get(header, None):
            headers[headers.index(header)] = index[header]
    return headers

def replace_variant_cv_field_values( object_class, headers, rows ):
    """Tries to replace variants of controlled-vocab with official values
    """
    def replace(fieldname, row, headers, rowd, index):
        """This does the actual work.
        """
        value = rowd.get(fieldname, None)
        # if value appears in index, it is a variant
        if value and index.get(value, None):
            row[headers.index(fieldname)] = index[value]
        return row
    
    for row in rows:
        rowd = make_row_dict(headers, row)
        row = replace('status', row, headers, rowd, STATUS_CHOICES_ALT_INDEX)
        row = replace('permissions', row, headers, rowd, PERMISSIONS_CHOICES_ALT_INDEX)
        row = replace('language', row, headers, rowd, LANGUAGE_CHOICES_ALT_INDEX)
        row = replace('genre', row, headers, rowd, GENRE_CHOICES_ALT_INDEX)
        row = replace('format', row, headers, rowd, FORMAT_CHOICES_ALT_INDEX)
    return rows


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
    
    headers = replace_variant_headers('entity', headers)
    rows = replace_variant_cv_field_values('entity', headers, rows)
    
    required_fields = get_required_fields('entity', ENTITY_FIELDS)
    # validate metadata before attempting import
    invalid_rows = all_rows_valid('entity', headers, required_fields, rows)
    if invalid_headers('entity', headers):
        print('FILE CONTAINS INVALID HEADERS - IMPORT CANCELLED')
    elif invalid_rows:
        print('FILE CONTAINS INVALID ROWS - IMPORT CANCELLED')
    else:
        collection = Collection.from_json(collection_path)
        print(collection)
        
        # --------------------------------------------------
        def prep_creators( data ): return [x.strip() for x in data.strip().split(';') if x]
        def prep_language( data ):
            """language can be 'eng', 'eng;jpn', 'eng:English', 'jpn:Japanese'
            """
            y = []
            for x in data.strip().split(';'):
                if ':' in x:
                    y.append(x.strip().split(':')[0])
                else:
                    y.append(x.strip())
            return y
        def prep_topics( data ): return [x.strip() for x in data.strip().split(';') if x]
        def prep_persons( data ): return [x.strip() for x in data.strip().split(';') if x]
        def prep_facility( data ): return [x.strip() for x in data.strip().split(';') if x]
        # --------------------------------------------------
        
        print('Data file looks ok')
        started = datetime.now()
        print('%s starting import' % dtfmt(started))
        print('')
        for n,row in enumerate(rows):
            rowstarted = datetime.now()
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
                                                 [settings.TEMPLATE_EJSON, settings.TEMPLATE_METS],
                                                 agent=AGENT)
            
            # reload newly-created Entity object
            entity = Entity.from_json(entity_path)
            
            # preppers
            rowd['creators'] = prep_creators(rowd['creators'])
            rowd['language'] = prep_language(rowd['language'])
            rowd['topics'] = prep_topics(rowd['topics'])
            rowd['persons'] = prep_persons(rowd['persons'])
            rowd['facility'] = prep_facility(rowd['facility'])
            
            # insert values from CSV
            for key in rowd.keys():
                setattr(entity, key, rowd[key])
            entity.record_created = datetime.now()
            entity.record_lastmod = datetime.now()
            
            # write back to file
            entity.dump_json()
            updated_files = [entity.json_path]
            exit,status = commands.entity_update(git_name, git_mail,
                                                 entity.parent_path, entity.id,
                                                 updated_files,
                                                 agent=AGENT)
            
            rowfinished = datetime.now()
            rowelapsed = rowfinished - rowstarted
            print('%s %s/%s %s (%s)' % (dtfmt(rowfinished), n+1, len(rows), entity.id, rowelapsed))
        finished = datetime.now()
        elapsed = finished - started
        print('')
        print('%s done (%s rows)' % (dtfmt(finished), len(rows)))
        print('%s elapsed' % elapsed)
        print('')


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
    
    headers = replace_variant_headers('file', headers)
    rows = replace_variant_cv_field_values('file', headers, rows)
    
    required_fields = get_required_fields('file', FILE_FIELDS)
    # validate metadata before attempting import
    invalid_rows = all_rows_valid('file', headers, required_fields, rows)
    if invalid_headers('file', headers):
        print('FILE CONTAINS INVALID HEADERS - IMPORT CANCELLED')
    elif invalid_rows:
        print('FILE CONTAINS INVALID ROWS - IMPORT CANCELLED')
    else:
        collection = Collection.from_json(collection_path)
        print(collection)
        
        #def prep_creators( data ): return [x.strip() for x in data.strip().split(';') if x]
        
        # load entities - if any Entities are missing this will error out
        bad_entities = test_entities(headers, rows)
        if bad_entities:
            print('ONE OR MORE OBJECTS ARE COULD NOT BE LOADED! - IMPORT CANCELLED!')
            for f in bad_entities:
                print('    %s' % f)
        # check for missing files
        missing_files = find_missing_files(csv_dir, headers, rows)
        if missing_files:
            print('ONE OR MORE SOURCE FILES ARE MISSING! - IMPORT CANCELLED!')
            for f in missing_files:
                print('    %s' % f)
        else:
            print('Source files present')
        # check for unreadable files
        unreadable_files = find_unreadable_files(csv_dir, headers, rows)
        if unreadable_files:
            print('ONE OR MORE SOURCE FILES COULD NOT BE OPENED! - IMPORT CANCELLED!')
            for f in unreadable_files:
                print('    %s' % f)
            print('Files must be readable to the user running this script (probably ddr).')
        else:
            print('Source files readable')
        
        # files are all accounted for, let's import
        if not (bad_entities or missing_files or unreadable_files):
            print('Data file looks ok and files are present')
            print('"$ tail -f /var/log/ddr/local.log" in a separate console for more details')
            started = datetime.now()
            print('%s starting import' % started)
            print('')
            for n,row in enumerate(rows):
                rowd = make_row_dict(headers, row)
                entity_id = rowd.pop('entity_id')
                repo,org,cid,eid = entity_id.split('-')
                entity_path = Entity.entity_path(None, repo, org, cid, eid)
                entity = Entity.from_json(entity_path)
                src_path = os.path.join(csv_dir, rowd.pop('basename_orig'))
                role = rowd.pop('role')
                rowstarted = datetime.now()
                print('%s %s/%s %s %s (%s)' % (dtfmt(rowstarted), n+1, len(rows), entity.id, src_path, humanize_bytes(os.path.getsize(src_path))))
                #print('add_file(%s, %s, %s, %s, %s, %s)' % (git_name, git_mail, entity, src_path, role, rowd))
                entity.add_file( git_name, git_mail, src_path, role, rowd, agent=AGENT )
                rowfinished = datetime.now()
                rowelapsed = rowfinished - rowstarted
                print('%s done (%s)' % (dtfmt(rowfinished), rowelapsed))
            finished = datetime.now()
            elapsed = finished - started
            print('')
            print('%s done (%s rows)' % (dtfmt(finished), len(rows)))
            print('%s elapsed' % elapsed)
            print('')


# export entities ------------------------------------------------------

def export_csv_path( collection_path, model ):
    collection_id = os.path.basename(collection_path)
    if model == 'entity':
        csv_filename = '%s-objects.csv' % collection_id
    elif model == 'file':
        csv_filename = '%s-files.csv' % collection_id
    csv_path = os.path.join(settings.CSV_TMPDIR, csv_filename)
    return csv_path

def export_entities( collection_path, csv_path ):
    """
    @param collection_path: Absolute path to collection repo.
    @param csv_path: Absolute path to CSV data file.
    """
    started = datetime.now()
    print('%s starting import' % started)
    make_tmpdir()
    fieldnames = [field['name'] for field in entitymodule.ENTITY_FIELDS]
    # exclude 'files' bc not hard to convert to CSV and not different from files export.
    fieldnames.remove('files')
    print(fieldnames)
    paths = []
    for path in metadata_files(basedir=collection_path, recursive=True):
        if os.path.basename(path) == 'entity.json':
            paths.append(path)
    
    with open(csv_path, 'wb') as csvfile:
        writer = make_csv_writer(csvfile)
        # headers
        writer.writerow(fieldnames)
        # everything else
        for n,path in enumerate(paths):
            rowstarted = datetime.now()
            
            entity_dir = os.path.dirname(path)
            entity_id = os.path.basename(entity_dir)
            entity = DDRLocalEntity.from_json(entity_dir)
            # seealso ddrlocal.models.__init__.module_function()
            values = []
            for f in entitymodule.ENTITY_FIELDS:
                value = ''
                if hasattr(entity, f['name']) and f.get('form',None):
                    key = f['name']
                    label = f['form']['label']
                    # run csvexport_* functions on field data if present
                    val = module_function(entitymodule,
                                          'csvexport_%s' % key,
                                          getattr(entity, f['name']))
                    if val:
                        value = str(val).encode('utf-8')
                values.append(value)
            writer.writerow(values)
            
            rowfinished = datetime.now()
            rowelapsed = rowfinished - rowstarted
            print('%s %s/%s %s (%s)' % (dtfmt(rowfinished), n+1, len(paths), entity_id, rowelapsed))
    
    finished = datetime.now()
    elapsed = finished - started
    print('%s DONE (%s entities)' % (dtfmt(finished), len(paths)))
    print('%s elapsed' % elapsed)
    if os.path.exists(csv_path):
        return csv_path
    return 'no file written'


# export files ---------------------------------------------------------

def export_files( collection_path, csv_path ):
    """
    @param collection_path: Absolute path to collection repo.
    @param csv_path: Absolute path to CSV data file.
    """
    started = datetime.now()
    print('%s starting import' % started)
    make_tmpdir()
    fieldnames = [field['name'] for field in filemodule.FILE_FIELDS]
    print(fieldnames)
    paths = []
    for path in metadata_files(basedir=collection_path, recursive=True):
        if ('master' in path) or ('mezzanine' in path):
            paths.append(path)
    
    with open(csv_path, 'wb') as csvfile:
        writer = make_csv_writer(csvfile)
        # headers
        writer.writerow(fieldnames)
        # everything else
        for n,path in enumerate(paths):
            rowstarted = datetime.now()
            
            # load file object
            filename = os.path.basename(path)
            file_id = os.path.splitext(filename)[0]
            file_ = DDRLocalFile.from_json(path)
            if file_:
                # seealso ddrlocal.models.__init__.module_function()
                values = []
                for f in filemodule.FILE_FIELDS:
                    value = ''
                    if hasattr(file_, f['name']):
                        key = f['name']
                        # run csvexport_* functions on field data if present
                        val = module_function(filemodule,
                                              'csvexport_%s' % key,
                                              getattr(file_, f['name']))
                        if val:
                            value = str(val).encode('utf-8')
                    values.append(value)
                writer.writerow(values)
            
                rowfinished = datetime.now()
                rowelapsed = rowfinished - rowstarted
                print('%s %s/%s %s (%s)' % (dtfmt(rowfinished), n+1, len(paths), file_id, rowelapsed))
            else:
                print('NO FILE FOR %s' % path)
    
    finished = datetime.now()
    elapsed = finished - started
    print('%s DONE (%s files)' % (dtfmt(finished), len(paths)))
    print('%s elapsed' % elapsed)
    if os.path.exists(csv_path):
        return csv_path
    return 'no file written'
