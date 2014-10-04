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
if REPO_MODELS_PATH not in sys.path:
    sys.path.append(REPO_MODELS_PATH)
try:
    from repo_models import collection as collectionmodule
    from repo_models import entity as entitymodule
    from repo_models import files as filemodule
except ImportError:
    # No Store mounted, no 'ddr' repository, or no valid repo_models in 'ddr'.
    raise Exception('Could not load repo_models.')


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

ALT_INDEXES = {
    'status': STATUS_CHOICES_ALT_INDEX,
    'permissions': PERMISSIONS_CHOICES_ALT_INDEX,
    'language': LANGUAGE_CHOICES_ALT_INDEX,
    'genre': GENRE_CHOICES_ALT_INDEX,
    'format': FORMAT_CHOICES_ALT_INDEX,
}

CHOICES_VALUES = {
}


def main():

    parser = argparse.ArgumentParser(description=description, epilog=epilog,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('csv', help='Absolute path to CSV file.')
    parser.add_argument('collection', help='Absolute path to Collection.')
    parser.add_argument('-u', '--user', required=True, help='User name')
    parser.add_argument('-m', '--mail', required=True, help='User e-mail address')
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
    
    batch.import_entities(args.csv, args.collection, args.user, args.mail)

if __name__ == '__main__':
    main()
