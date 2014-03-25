from datetime import datetime, date
import json
import logging
logger = logging.getLogger(__name__)

#from lxml import etree

import tematres



DEFAULT_PERMISSION_ENTITY = 1
DEFAULT_RIGHTS_ENTITY = 'cc'

DATE_FORMAT            = '%Y-%m-%d'
TIME_FORMAT            = '%H:%M:%S'
DATETIME_FORMAT        = '%Y-%m-%dT%H:%M:%S'
PRETTY_DATE_FORMAT     = '%d %B %Y'
PRETTY_TIME_FORMAT     = '%I:%M %p'
PRETTY_DATETIME_FORMAT = '%d %B %Y, %I:%M %p'

STATUS_CHOICES = [['inprocess', 'In Progress'],
                  ['completed', 'Completed'],]

PERMISSIONS_CHOICES = [['1','Public'],
                       ['0','Private'],]
					
RIGHTS_CHOICES = [["cc", "DDR Creative Commons"],
                  ["pcc", "Copyright, with special 3rd-party grant permitted"],
                  ["nocc", "Copyright restricted"],
                  ["pdm", "Public domain" ],]

LANGUAGE_CHOICES = [['',''],
                    ['eng','English'],
                    ['jpn','Japanese'],
                    ['chi','Chinese'],
                    ['fre','French'],
                    ['ger','German'],
					['ita', 'Italian'],
                    ['kor','Korean'],
                    ['por','Portuguese'],
                    ['rus','Russian'],
                    ['spa','Spanish'],
                    ['tgl','Tagalog'],]

GENRE_CHOICES = [['advertisement','Advertisements'],
                 ['album','Albums'],
                 ['architecture','Architecture'],
                 ['baseball_card','Baseball Cards'],
                 ['blank_form','Blank Forms'],
                 ['book','Books'],
                 ['broadside','Broadsides'],
                 ['cartoon','Cartoons (Commentary)'],
                 ['catalog','Catalogs'],
                 ['cityscape','Cityscapes'],
                 ['clipping','Clippings'],
                 ['correspondence','Correspondence'],
                 ['diary','Diaries'],
                 ['drawing','Drawings'],
                 ['ephemera','Ephemera'],
                 ['essay','Essays'],
                 ['ethnography','Ethnography'],
                 ['fieldnotes','Fieldnotes'],
                 ['illustration','Illustrations'],
                 ['interview','Interviews'],
                 ['landscape','Landscapes'],
                 ['leaflet','Leaflets'],
                 ['manuscript','Manuscripts'],
                 ['map','Maps'],
                 ['misc_document','Miscellaneous Documents'],
                 ['motion_picture','Motion Pictures'],
                 ['music','Music'],
                 ['narrative','Narratives'],
                 ['painting','Paintings'],
                 ['pamphlet','Pamphlets'],
                 ['periodical','Periodicals'],
                 ['petition','Petitions'],
                 ['photograph','Photographs'],
                 ['physical_object','Physical Objects'],
                 ['poetry','Poetry'],
                 ['portrait','Portraits'],
                 ['postcard','Postcards'],
                 ['poster','Posters'],
                 ['print','Prints'],
                 ['program','Programs'],
                 ['rec_log','Recording Logs'],
                 ['score','Scores'],
                 ['sheet_music','Sheet Music'],
                 ['timetable','Timetables'],
                 ['transcription','Transcriptions'],]

FORMAT_CHOICES = [['av','Audio/Visual'],
                  ['ds','Dataset'],
                  ['doc','Document'],
                  ['img','Still Image'],
                  ['vh','Oral History'],]

ENTITY_FIELDS = [
    {
        'name':       'id',
        'xpath':      "/mets:mets/@OBJID",
        'xpath_dup':  [
            "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:identifier",
            #"/mets:mets/mets:amdSec/mets:digiProvMD[@ID='PROV1']/mets:mdWrap/mets:xmlData/premis:premis/premis:object/premis:objectIdentifierValue",
            ],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Object ID',
            'help_text':  '',
            'max_length': 255,
            'widget':     'HiddenInput',
            'initial':    '',
            'required':   True,
        },
        'default':    '',
    },
    {
        'name':       'record_created',
        'xpath':      "/mets:mets/mets:metsHdr@CREATEDATE",
        'xpath_dup':  [],
        'model_type': datetime,
        'form_type':  'DateTimeField',
        'form': {
            'label':      'Record Created',
            'help_text':  '',
            'widget':     'HiddenInput',
            'initial':    '',
            'required':   True,
        },
        'default':    '',
    },
    {
        'name':       'record_lastmod',
        'xpath':      "/mets:mets/mets:metsHdr@LASTMODDATE",
        'xpath_dup':  [],
        'model_type': datetime,
        'form_type':  'DateTimeField',
        'form': {
            'label':      'Record Modified',
            'help_text':  '',
            'widget':     'HiddenInput',
            'initial':    '',
            'required':   True,
        },
        'default':    '',
    },
    {
        'name':       'status',
        'group':      '',
        'xpath':      "",
        'xpath_dup':  [],
        'inheritable':True,
        'model_type': int,
        'form_type':  'ChoiceField',
        'form': {
            'label':      'Production Status',
            'help_text':  '"In Progress" = the object is not ready for release on the DDR public website. (The object will not be published even if the collection has a status of "Complete".) "Complete" = the object is ready for release on the DDR public website. (The object can only be published if the collection has a status of "Complete".)',
            'widget':     '',
            'choices':    STATUS_CHOICES,
            'initial':    '',
            'required':   True,
        },
        'default':    '',
    },
    {
        'name':       'public',
        'group':      '',
        'xpath':      "",
        'xpath_dup':  [],
        'inheritable':True,
        'model_type': int,
        'form_type':  'ChoiceField',
        'form': {
            'label':      'Privacy Level',
            'help_text':  '"Public" = the object is viewable through the DDR public website. (Any files under the object with a status of "Private" will not be viewable regardless of the object\'s privacy level. If the entire collection has a status of "Private" no objects or files will be viewable). "Private" = the object is restricted and not viewable through the DDR public website. (Any files under the object inherit this privacy level and will not be viewable either. If the entire collection has a status of "Public" the object will remain not viewable).',
            'widget':     '',
            'choices':    PERMISSIONS_CHOICES,
            'initial':    DEFAULT_PERMISSION_ENTITY,
            'required':   True,
        },
        'default':    '',
    },
    {
        'name':       'title',
        'xpath':      "/mets:mets/@LABEL",
        'xpath_dup':  [
            "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:titleInfo/mods:title",
            ],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Title',
            'help_text':  'Use an original or previously designated title if one exists. If an original does not exist one should be derived. For derived titles, capitalize the first word and proper nouns and there is no period at end of the title. If the subject is completely unidentifiable, then use of "Unknown" can be appropriate.',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   True,
        },
        'default':    '',
    },
    {
        'name':       'description',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:abstract",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Description',
            'help_text':  'Use if the title field is not sufficient for the amount of information you have about the object. The description can also include transcriptions of anything handwritten, stamped, or printed on the material. In such cases, specify that is how the information originated. Follow Chicago Manual of Style guidelines for text.',
            'max_length': 4000,
            'widget':     'Textarea',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    {
        'name':       'creation',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:originInfo/mods:dateCreated",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Date (Created)',
            'help_text':  'f the exact date is known use MM/DD/YYY for the format. If the exact date is unknown, then use circa (c.1931) or if applicable, a date range (1930-1940).',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    {
        'name':       'location',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:originInfo/mods:place/mods:placeTerm[@type='text']",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Location',
            'help_text':  'When possible use the Getty Thesaurus of Geographic names as an authority. Format the names as follows: City, State (state name spelled out). Include country if outside the United States (i.e., City, State, Country).',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    {
        'name':       'creators',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:name/mods:namePart",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Creator',
            'help_text':  'When possible use the Library of Congress Name Authority Headings. For individuals use the following format: "Last Name, First Name: Creator Role" (e.g., Adams, Ansel:photographer). For organizations use the following format: "Organization Name: Creator Role" (e.g., Associated Press:publisher). Multiple creators are allowed, but must be separated using a semi-colon.',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    {
        'name':       'language',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:language/mods:languageTerm",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'MultipleChoiceField',
        'form': {
            'label':      'Language',
            'help_text':  'Only needed for objects containing textual content (i.e. caption on a photograph, text of a letter). To select multiple languages hold the Ctrl key down and click on each language.',
            'choices':  LANGUAGE_CHOICES,
            'widget':     '',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    {
        'name':       'genre',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:genre",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'ChoiceField',
        'form': {
            'label':      'Object Genre',
            'help_text':  'The genre, form, and/or physical characteristics of the object.	Use the Library of Congress Basic Genre Terms for Cultural Heritage Materials controlled vocabulary list. See Appendix E: Controlled Vocabularies or the Library of Congress website: http://memory.loc.gov/ammem/techdocs/genre.html',
            'choices': GENRE_CHOICES,
            'widget':     '',
            'initial':    '',
            'required':   True,
        },
        'default':    '',
    },
    {
        'name':       'format',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:typeOfResource",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'ChoiceField',
        'form': {
            'label':      'Object Format',
            'help_text':  'A descriptor for indicating the type of object.	Use the Densho Object Type Controlled Vocabulary List found in Appendix E: Controlled Vocabularies.',
            'choices': FORMAT_CHOICES,
            'widget':     '',
            'initial':    '',
            'required':   True,
        },
        'default':    '',
    },
    {
        'name':       'extent',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:physicalDescription/mods:extent",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Physical Description',
            'help_text':  'Optional: extent, media-type, and any additional relevant information about the material. (e.g. 1 scrapbook, 1 photograph). Construct the statement using a standard like AACR2, RDA, DACS or DCRM(G). Required: width in inches, followed by height in inches, in the following format: "5.25W x 3.5H". For photographs, do not include border, mounts and/or frames. Separate the extent/media-type and the dimensions with a colon. (e.g. 1 scrapbook: 8W x 10H).',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   True,
        },
        'default':    '',
    },
    {
        'name':       'contributor',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:location/mods:physicalLocation",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Contributing Institution',
            'help_text':  'Name of the organization that owns the physical materials. Will probably be the name of the partner, unless materials were borrowed from external institution for scanning.',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   True,
        },
        'default':    '',
    },
    {
        'name':       'alternate_id',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:location/mods:holdingExternal/mods:institutionIdentifier/mods:value",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Alternate ID',
            'help_text':  'May be a physical or virtual record identifier. For example, a physical shelf/folder location, a negative number, an accession number, or a URI of an external database record.',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    {
        'name':       'digitize_person',
        'xpath':      '',
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Digitizer',
            'help_text':  'Name of person who created the scan. LastName, FirstName',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    {
        'name':       'digitize_organization',
        'xpath':      '',
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Digitizing Institution',
            'help_text':  'Name of organization responsible for scanning. Will probably be the name of the partner.',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    {
        'name':       'digitize_date',
        'xpath':      '',
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Digitize Date',
            'help_text':  'Date of scan. M/D/YYYY.',
            'widget':     '',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    # technical
    {
        'name':       'credit',
        'xpath':      '',
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Preferred Citation',
            'help_text':  'Short courtesy text relating to use of object. Could identify either collection contributor and/or donor depending on deed of gift and/or usage agreement for object. Often begins with: "Courtesy of..."',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   True,
        },
        'default':    '',
    },
    {
        'name':       'rights',
        'group':      '',
        'xpath':      "",
        'xpath_dup':  [],
        'inheritable':True,
        'model_type': str,
        'form_type':  'ChoiceField',
        'form': {
            'label':      'Rights',
            'help_text':  'Use rights for the object. Setting will determine the initial default for files associated with this object.',
            'widget':     '',
            'choices':    RIGHTS_CHOICES,
            'initial':    DEFAULT_RIGHTS_ENTITY,
            'required':   True,
        },
        'default':    '',
    }, 
    {
        'name':       'rights_statement',
        'xpath':      '',
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Restrictions on Reproduction and Use',
            'help_text':  'Short text statement about copyright status, who owns copyright, contact information for requests for use, etc.',
            'widget':     'Textarea',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    {
        'name':       'topics',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:subject/mods:topic/@xlink:href",
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:subject",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Topic',
            'help_text':  'Use the Densho Topics Controlled Vocabulary List found in Appendix E: Controlled Vocabularies. Multiple entries allowed; separate with a semi-colon. Include the topic ID in brackets after each topic.',
            'widget':     'Textarea',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    {
        'name':       'persons',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:subject[@ID='persons']",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Person/Organization',
            'help_text':  'When possible use the Library of Congress Name Authority Headings. For individuals use the following format: "Last Name, First Name" (e.g., Adams, Ansel). For organizations use the following format: "Organization Name" (e.g., Associated Press). 			Multiple creators are allowed, but must be separated using a semi-colon.',
            'widget':     'Textarea',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    {
        'name':       'facility',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:subject/mods:geographic",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Facility',
            'help_text':  'Use the Densho Facilities Controlled Vocabulary List found in Appendix E: Controlled Vocabularies. Multiple entries allowed; separate with a semi-colon.',
            'widget':     'Textarea',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    {
        'name':       'parent',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:relatedItem/mods:identifier[@type='local']",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Parent Object',
            'help_text':  'Identifier of the object that contains this object. (I.e., the scrapbook that the photo belongs to)	Must be an existing DDR Object ID',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    {
        'name':       'notes',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:note/",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Notes',
            'help_text':  'This is an internal field that is not viewable through the public website.',
            'widget':     'Textarea',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    {
        'name':       'files',
        'xpath':      "",
        'xpath_dup':  [],
        'model_type': str,
        # no form_type
        # no form
        'default':    '',
    },
]



# display_* --- Display functions --------------------------------------
#
# These functions take Python data from the corresponding Entity field
# and format it for display.
#

# id

def display_record_created( data ):
    if type(data) == type(datetime.now()):
        data = data.strftime(PRETTY_DATETIME_FORMAT)
    return data

def display_record_lastmod( data ):
    if type(data) == type(datetime.now()):
        data = data.strftime(PRETTY_DATETIME_FORMAT)
    return data

def display_status( data ):
    for c in STATUS_CHOICES:
        if data == c[0]:
            return c[1]
    return data

def display_public( data ):
    for c in PERMISSIONS_CHOICES:
        if data == c[0]:
            return c[1]
    return data

def display_rights( data ):
    for c in RIGHTS_CHOICES:
        if data == c[0]:
            return c[1]
    return data

# collection
# title
# description
# creation
# location

def display_creators( data ):
    return _display_multiline_dict('<a href="{namepart}">{role}: {namepart}</a>', data)

def display_language( data ):
    labels = []
    for c in LANGUAGE_CHOICES:
        if c[0] in data:
            labels.append(c[1])
    if labels:
        return ', '.join(labels)
    return ''

def display_genre( data ):
    for c in GENRE_CHOICES:
        if data == c[0]:
            return c[1]
    return data

def display_format( data ):
    for c in FORMAT_CHOICES:
        if data == c[0]:
            return c[1]
    return data

# dimensions
# organization
# organization_id
# digitize_person
# digitize_organization
# digitize_date
# credit

def display_topics( data ):
    return _display_multiline_dict('<a href="{url}">{label}</a>', data)

def display_persons( data ):
    d = []
    for line in data:
        d.append({'person': line.strip()})
    return _display_multiline_dict('<a href="{person}">{person}</a>', d)

#def display_facility( data ):
#    d = []
#    for line in data:
#        d.append({'facility': line.strip()})
#    return _render_multiline_dict('<a href="">{facility}</a>', d)

# parent
# notes
# files

# The following are utility functions used by functions.

def _display_multiline_dict( template, data ):
    t = []
    for x in data:
        if type(x) == type({}):
            t.append(template.format(**x))
        else:
            t.append(x)
    return '\n'.join(t)



# formprep_* --- Form pre-processing functions.--------------------------
#
# These functions take Python data from the corresponding Entity field
# and format it so that it can be used in an HTML form.
#
                   
# id
# record_created
# record_lastmod
# public
# rights

def formprep_parent(data):     return _formprep_basic(data)

# title
# description
# creation
# location

def formprep_creators(data):
    """Takes list of names and formats into "NAME:ROLE;\nNAME:ROLE"
    
    >>> data0 = ['Watanabe, Joe']
    >>> formprep_creators(data0)
    'Watanabe, Joe:author'
    >>> data1 = ['Masuda, Kikuye:author']
    >>> formprep_creators(data1)
    'Masuda, Kikuye:author'
    >>> data2 = [{'namepart':'Boyle, Rob:concept,editor', 'role':'author'}, {'namepart':'Cross, Brian:concept,editor', 'role':'author'}]
    >>> formprep_creators(data2)
    'Boyle, Rob:concept,editor;\nCross, Brian:concept,editor'
    """
    names = []
    # split string into list
    if isinstance(data, basestring) and (';' in data):
        data = data.split(';')
    # prep list of names (we hope that's what it is)
    if isinstance(data, list):
        for n in data:
            if isinstance(n, dict):
                # data1: dict with namepart and role in separate fields
                if ':' in n['namepart']: # often role was put in name field
                    names.append(n['namepart'])
                else:
                    names.append( ':'.join([ n['namepart'], n['role'] ]) )
            elif isinstance(n, basestring):
                # data2
                if ':' in n:
                    names.append(n)
                else:
                    names.append('%s:author' % n)
            else:
                assert False
    data = ';\n'.join(names)
    return data

# genre
# format
# dimensions
# organization
# organization_id
# digitize_person
# digitize_organization
# digitize_date
# credit

def formprep_topics(data):
    """Present as semicolon-separated list"""
    a = []
    for t in data:
        if type(t) == type({}):
            x = t['url']
        else:
            x = t
        a.append(x)
    return ';\n'.join(a)

def formprep_persons(data):
    return ';\n'.join(data)

def formprep_facility(data):   return _formprep_basic(data)

# notes

# The following are utility functions used by formprep_* functions.

def _formprep_basic(data):
    if data:
        return json.dumps(data)
    return ''



# formpost_* --- Form post-processing functions ------------------------
#
# These functions take data from the corresponding form field and turn it
# into Python objects that are inserted into the Entity.
#

# id
# record_created
# record_lastmod
# public
# rights

def formpost_parent(data):     return _formpost_basic(data)

# title
# description
# creation
# location

def formpost_creators(data):
    """Splits up data into separate names, each with namepart and role.
    
    >>> data0 = "Watanabe, Joe"
    >>> formpost_creators(data0)
    [{'namepart': 'Watanabe, Joe', 'role': 'author'}]
    >>> data1 = "Masuda, Kikuye:author"
    >>> formpost_creators(data1)
    [{'namepart': 'Masuda, Kikuye', 'role': 'author'}]
    >>> data2 = "Boyle, Rob:concept,editor; Cross, Brian:concept,editor"
    >>> formpost_creators(data2)
    [{'namepart': 'Boyle, Rob', 'role': 'concept,editor'}, {'namepart': 'Cross, Brian', 'role': 'concept,editor'}]
    """
    a = []
    for n in data.split(';'):
        if ':' in n:
            name,role = n.strip().split(':')
        else:
            name = n.strip(); role = 'author'
        b = {'namepart': name.strip(), 'role': role.strip(),}
        a.append(b)
    return a

# genre
# format
# dimensions
# organization
# organization_id
# digitize_person
# digitize_organization
# digitize_date
# credit

def formpost_topics(data):
    a = []
    form_urls = [t.strip() for t in data.split(';')]
    a = tematres.get_terms(form_urls)
    return a

def formpost_persons(data):
    return [n.strip() for n in data.split(';')]

def formpost_facility(data):   return _formpost_basic(data)

# notes

# The following are utility functions used by formpost_* functions.

def _formpost_basic(data):
    if data:
        try:
            return json.loads(data)
        except:
            return data
    return ''



# mets_* --- METS XML export functions ---------------------------------
#
# These functions take Python data from the corresponding Entity field
# and write it to a METS XML document.
#

def mets_id(tree, namespaces, field, value):
    tree = _set_attr(tree, namespaces, '/mets:mets', 'OBJID', value)
    tree = _set_tag_text(tree, namespaces,
                         "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:identifier",
                         value)
    #tree = _set_tag_text(tree, namespaces,
    #                     "/mets:mets/mets:amdSec/mets:digiProvMD[@ID='PROV1']/mets:mdWrap/mets:xmlData/premis:premis/premis:object/premis:objectIdentifierValue",
    #                     value)
    return tree

def mets_record_created(tree, namespaces, field, value):
    if type(value) == type(datetime.now()):
        value = value.strftime(DATETIME_FORMAT)
    return _set_attr(tree, namespaces, '/mets:mets/mets:metsHdr', 'CREATEDATE', value)

def mets_record_lastmod(tree, namespaces, field, value):
    try:
        value = value.strftime(DATETIME_FORMAT)
    except:
        pass
    return _set_attr(tree, namespaces, '/mets:mets/mets:metsHdr', 'LASTMODDATE', value)

# public
# rights
# parent
# collection

def mets_title(tree, namespaces, field, value):
    tree = _set_attr(tree, namespaces, '/mets:mets', 'LABEL', value)
    tree = _set_tag_text(tree, namespaces, "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:titleInfo/mods:title", value)
    return tree

def mets_description(tree, namespaces, field, value):
    return _set_tag_text(tree, namespaces, field['xpath'], value)

# creation
# location

def mets_creators(tree, namespaces, field, value):
    """
    <mods:name authority="naf" type="organization">
      <mods:namePart>Anderson Photo Service</mods:namePart>
      <mods:role>
        <mods:roleTerm authority="marcrelator" type="text">Artist</mods:roleTerm>
      </mods:role>
    </mods:name>
    """
    return tree

def mets_language(tree, namespaces, field, value):
    """
    """
    return tree

# genre
# format
# dimensions
# organization
# organization_id
# digitize_person
# digitize_organization
# digitize_date
# credit

def mets_topics(tree, namespaces, field, value):
    """
    <mods:subject ID="topics">
      <mods:topic xlink:href="http://id.densho.org/cv/topics/8">Small Business [8]</mods:topic>
      ...
    </mods:subject>
    """
    ## remove existing tags
    #parent = None
    #for tag in tree.xpath(field['xpath'], namespaces=namespaces):
    #    parent = tag.getparent()
    #    parent.remove(tag)
    ## replace with new tags
    #if parent:
    #    for kv in value:
    #        tag = etree.Element(_expand_attrib_namespace('mods:topic', namespaces))
    #        tag.set(_expand_attrib_namespace('xlink:href', namespaces), kv['url'])
    #        tag.text = kv['label']
    #        parent.append(tag)
    return tree

def mets_persons(tree, namespaces, field, value):
    """
    <mods:subject ID="persons">
      <mods:name authority="naf" type="personal">
        <mods:namePart>Hatchimonji, Kumezo</mods:namePart>
      </mods:name>
      ...
    </mods:subject>
    """
    #parent = None
    #xpath = field['xpath']
    #tags = tree.xpath(field['xpath'], namespaces=namespaces)
    #assert False
    ## replace with new tags
    #if parent:
    #    for kv in value:
    #        name = etree.Element(_expand_attrib_namespace('mods:name', namespaces))
    #        name.set('authority', 'naf')
    #        name.set('type', 'unknown')
    #        namePart = etree.Element(_expand_attrib_namespace('mods:namePart', namespaces))
    #        namePart.text = kv
    #        name.append(namePart)
    #        parent.append(name)
    return tree

# facility
# notes
# files

# The following are utility functions used by mets_* functions.

def _expand_attrib_namespace(attr, namespaces):
    ns,a = attr.split(':')
    return '{%s}%s' % (namespaces[ns], a)

def _getval(tree, namespaces, xpath):
    """Gets the first value; yes this is probably suboptimal
    """
    return tree.xpath(xpath, namespaces=namespaces)[0]

def _set_attr(tree, namespaces, xpath, attr, value):
    tag = tree.xpath(xpath, namespaces=namespaces)[0]
    tag.set(attr, value)
    return tree

def _set_tag_text(tree, namespaces, xpath, value):
    tag = _getval(tree, namespaces, xpath)
    tag.text = value
    return tree

def _duplicate(tree, namespaces, src_xpath, dest_xpath):
    i = tree.xpath( src_xpath,  namespaces=namespaces )[0]
    tag = tree.xpath( dest_xpath, namespaces=namespaces )[0]
    tag.text = i
    return tree

def _mets_simple(tree, namespaces, field, value):
    return _set_tag_text(tree, namespaces, field['xpath'], value)
