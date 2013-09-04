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

STATUS_CHOICES = [['inprocess', 'In Process'],
                  ['completed', 'Completed'],]

PERMISSIONS_CHOICES = [['1','Public'],
                       ['0','Private'],]
					
RIGHTS_CHOICES = [['',''],
                  ['cc','DDR Creative Commons'],
                  ['nocc','Copyright restricted'],
                  ['pdm','Public domain'],]

LANGUAGE_CHOICES = [['',''],
                    ['eng','English'],
                    ['jpn','Japanese'],
                    ['chi','Chinese'],
                    ['fre','French'],
                    ['ger','German'],
                    ['kor','Korean'],
                    ['por','Portuguese'],
                    ['rus','Russian'],
                    ['spa','Spanish'],
                    ['tgl','Tagalog'],]

GENRE_CHOICES = [['advertisement','Advertisement'],
                 ['album','Album'],
                 ['architecture','Architecture'],
                 ['baseball_card','Baseball Card'],
                 ['blank_form','Blank Form'],
                 ['book','Book'],
                 ['broadside','Broadside'],
                 ['cartoon','Cartoon (Commentary)'],
                 ['catalog','Catalog'],
                 ['cityscape','Cityscape'],
                 ['clipping','Clipping'],
                 ['correspondence','Correspondence'],
                 ['diary','Diary'],
                 ['drawing','Drawing'],
                 ['ephemera','Ephemera'],
                 ['essay','Essay'],
                 ['ethnography','Ethnography'],
                 ['fieldnotes','Fieldnotes'],
                 ['illustration','Illustration'],
                 ['interview','Interview'],
                 ['landscape','Landscape'],
                 ['leaflet','Leaflet'],
                 ['manuscript','Manuscript'],
                 ['map','Map'],
                 ['misc_document','Miscellaneous Document'],
                 ['motion_picture','Motion Picture'],
                 ['music','Music'],
                 ['narrative','Narrative'],
                 ['painting','Painting'],
                 ['pamphlet','Pamphlet'],
                 ['periodical','Periodical'],
                 ['petition','Petition'],
                 ['photograph','Photograph'],
                 ['physical_object','Physical Object'],
                 ['poetry','Poetry'],
                 ['portrait','Portrait'],
                 ['postcard','Postcard'],
                 ['poster','Poster'],
                 ['print','Print'],
                 ['program','Program'],
                 ['rec_log','Recording Log'],
                 ['score','Score'],
                 ['sheet_music','Sheet Music'],
                 ['timetable','Timetable'],
                 ['transcription','Transcription'],]

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
        'name':       'created',
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
        'name':       'lastmod',
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
        'model_type': int,
        'form_type':  'ChoiceField',
        'form': {
            'label':      'Production Status',
            'help_text':  '',
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
        'model_type': int,
        'form_type':  'ChoiceField',
        'form': {
            'label':      'Privacy Level',
            'help_text':  'Setting applies permission to everything under this object.',
            'widget':     '',
            'choices':    PERMISSIONS_CHOICES,
            'initial':    DEFAULT_PERMISSION_ENTITY,
            'required':   True,
        },
        'default':    '',
    },
    {
        'name':       'rights',
        'group':      '',
        'xpath':      "",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'ChoiceField',
        'form': {
            'label':      'Rights',
            'help_text':  'Setting will determine the initial default for files associated with this object.',
            'widget':     '',
            'choices':    RIGHTS_CHOICES,
            'initial':    DEFAULT_RIGHTS_ENTITY,
            'required':   True,
        },
        'default':    '',
    },

    # Scan ID
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
            'help_text':  'A short title for the object. Use original title if exists.	Capitalize first word and proper nouns. No period at end of title. If subject is completely unidentifiable, then use, "Unknown"',
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
            'help_text':  'A caption describing the content and/or subject of the object.	Brief free text following basic Chicago Manual style guidelines.',
            'max_length': 255,
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
            'help_text':  'Date of original creation. Not the digitization date. M/D/YYYY. If exact date is not known, then use circa ("c. 1931") or if applicable, a date range ("1930-1940").',
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
            'help_text':  'Geographic area of the subject (i.e., where a photograph was taken). Could be place of creation for a document.	City, State (state name spelled out). Include country if outside the US (i.e., City, State, Country).',
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
            'help_text':  'For photographs, the name of the photographer. For letters, documents and other written materials, the name of the author. For newspapers, magazine and other printed matter, the name of the publisher.	For individuals, "LastName, FirstName: CreatorRole" (e.g., "Adams, Ansel:photographer"). Multiple creators are allowed, but must be separated using a semi-colon.',
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
            'help_text':  '',
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
        'name':       'dimensions',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:physicalDescription/mods:extent",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Physical Dimensions',
            'help_text':  'The size of the original physical object. Width in inches, followed by height in inches, in the following format: "5.25W x 3.5H". For photographs, do not include border, mounts and/or frames.',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   True,
        },
        'default':    '',
    },
    {
        'name':       'organization',
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
        'name':       'organization_id',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:location/mods:holdingExternal/mods:institutionIdentifier/mods:value",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Contributing Institution ID',
            'help_text':  'An identifier for the physical object from the originating institution. (How would a user locate the original physical object?)	May be a physical or virtual record identifier. For example, a physical shelf/folder location, a negative number, an accession number, or a URI of an external database record.',
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
        'form_type':  'DateField',
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
            'label':      'Credit Line',
            'help_text':  'Short courtesy text relating to use of object. Could identify either collection contributor and/or donor depending on deed of gift and/or usage agreement for object. Always begins with: "Courtesy of"',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   True,
        },
        'default':    '',
    },
    {
        'name':       'rights',
        'xpath':      '',
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Rights and Restrictions',
            'help_text':  'Short statement about usage limitations and intellectual property for the individual object. Only needs to be filled out if the individual object has restrictions different than those of the parent collection.',
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
            'help_text':  'Thematic content of object.	From Densho topics controlled vocabulary. Separate multiple topics with semi-colon.',
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
            'help_text':  'People and/or organizations that are represented in the object.	For people: LastName, FirstName. Separate multiple entries with semi-colon.',
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
            'help_text':  'Confinement site associated with the content of the object. From controlled vocabulary. Separate multiple entries with semi-colon.',
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
            'help_text':  'Identifier of the object that contains this object. (I.e., the scrapbook that the photo belongs to)	Must be an existing ID',
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
            'help_text':  '',
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

def display_created( data ):
    if type(data) == type(datetime.now()):
        data = data.strftime(PRETTY_DATETIME_FORMAT)
    return data

def display_lastmod( data ):
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

def display_digitize_date( data ):
    if type(data) == type(datetime.now()):
        data = data.strftime(PRETTY_DATE_FORMAT)
    return data

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
# created
# lastmod
# public
# rights

def formprep_parent(data):     return _formprep_basic(data)

# title
# description
# creation
# location

def formprep_creators(data):
    data = ';\n'.join([n['namepart'] for n in data])
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
# created
# lastmod
# public
# rights

def formpost_parent(data):     return _formpost_basic(data)

# title
# description
# creation
# location

def formpost_creators(data):
    a = []
    for n in data.split(';'):
        b = {'namepart': n.strip(), 'role': 'author',}
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

def mets_created(tree, namespaces, field, value):
    if type(value) == type(datetime.now()):
        value = value.strftime(DATETIME_FORMAT)
    return _set_attr(tree, namespaces, '/mets:mets/mets:metsHdr', 'CREATEDATE', value)

def mets_lastmod(tree, namespaces, field, value):
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
