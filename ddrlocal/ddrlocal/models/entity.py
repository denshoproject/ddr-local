from datetime import datetime, date
import json

#from lxml import etree

from django import forms
from django.conf import settings

import tematres



LANGUAGE_CHOICES = [['eng','English'],
                    ['jpn','Japanese'],
                    ['esp','Spanish'],]

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

FORMAT_CHOICES = [['photo','Photo'],
                    ['doc','Document'],
                    ['vh','Oral History'],]



# forms pre-processing functions ---------------------------------------
# convert from Python objects to form(data)

def _prepare_basic(data):
    if data:
        return json.dumps(data)
    return ''
                   
# id
# created
# lastmod
def prepare_parent(data):     return _prepare_basic(data)
def prepare_collection(data): return _prepare_basic(data)
# title
# description
def prepare_creation(data):   return _prepare_basic(data)
# location

def prepare_creators(data):
    data = ';\n'.join([n['namepart'] for n in data])
    return data

def prepare_language(data):
    if data.get('code', None):
        data = data['code']
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
# rights

def prepare_topics(data):
    """Present as semicolon-separated list"""
    a = [t['url'] for t in data]
    data = ';\n'.join(a)
    return data

def prepare_persons(data):
    return ';\n'.join(data)

def prepare_facility(data):   return _prepare_basic(data)
# notes



# forms post-processing functions --------------------------------------
# convert from form.cleaned_data to Python objects

def _process_basic(data):
    if data:
        try:
            return json.loads(data)
        except:
            return data
    return ''

# id
# created
# lastmod
def process_parent(data):     return _process_basic(data)
def process_collection(data): return _process_basic(data)
# title
# description
def process_creation(data):   return _process_basic(data)
# location

def process_creators(data):
    a = []
    for n in data.split(';'):
        b = {'namepart': n.strip(), 'role': 'author',}
        a.append(b)
    return a

def process_language(data):
    a = {'code': data,
         'label': '',}
    for l in LANGUAGE_CHOICES:
        if l[0] == a['code']:
            a['label'] = l[1]
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
# rights

def process_topics(data):
    a = []
    form_urls = [t.strip() for t in data.split(';')]
    a = tematres.get_terms(form_urls)
    return a

def process_persons(data):
    return [n.strip() for n in data.split(';')]

def process_facility(data):   return _process_basic(data)
# notes



# XML export functions -------------------------------------------------
# 

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
        value = value.strftime(settings.DATETIME_FORMAT)
    return _set_attr(tree, namespaces, '/mets:mets/mets:metsHdr', 'CREATEDATE', value)

def mets_lastmod(tree, namespaces, field, value):
    try:
        value = value.strftime(settings.DATETIME_FORMAT)
    except:
        pass
    return _set_attr(tree, namespaces, '/mets:mets/mets:metsHdr', 'LASTMODDATE', value)

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
# rights

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



ENTITY_FIELDS = [
    {
        'name':       'id',
        'xpath':      "/mets:mets/@OBJID",
        'xpath_dup':  [
            "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:identifier",
            #"/mets:mets/mets:amdSec/mets:digiProvMD[@ID='PROV1']/mets:mdWrap/mets:xmlData/premis:premis/premis:object/premis:objectIdentifierValue",
            ],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Object ID',
            'help_text':  '',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   True,
        },
        'mets_func':  mets_id,
        'default':    '',
    },
    {
        'name':       'created',
        'xpath':      "/mets:mets/mets:metsHdr@CREATEDATE",
        'xpath_dup':  [],
        'model_type': datetime,
        'form_type':  forms.DateTimeField,
        'form': {
            'label':      'Record Created',
            'help_text':  '',
            'widget':     forms.HiddenInput,
            'initial':    '',
            'required':   True,
        },
        'mets_func':  mets_created,
        'default':    '',
    },
    {
        'name':       'lastmod',
        'xpath':      "/mets:mets/mets:metsHdr@LASTMODDATE",
        'xpath_dup':  [],
        'model_type': datetime,
        'form_type':  forms.DateTimeField,
        'form': {
            'label':      'Record Modified',
            'help_text':  '',
            'widget':     forms.HiddenInput,
            'initial':    '',
            'required':   True,
        },
        'mets_func':  mets_lastmod,
        'default':    '',
    },
    {
        'name':       'parent',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:relatedItem/mods:identifier[@type='local']",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Parent Object',
            'help_text':  'Identifier of the object that contains this object. (I.e., the scrapbook that the photo belongs to)	Must be an existing ID',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   False,
        },
        'prep_func':  prepare_parent,
        'proc_func':  process_parent,
        'default':    '',
    },
    {
        'name':       'collection',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:relatedItem[@displayLabel='Collection' and @type='host']/mods:identifier[@type='local']",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Collection',
            'help_text':  'Name of collection	Must refer to existing partner collection. See reference on collections.',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   True,
        },
        'prep_func':  prepare_collection,
        'proc_func':  process_collection,
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
        'form_type':  forms.CharField,
        'form': {
            'label':      'Title',
            'help_text':  'A short title for the object. Use original title if exists.	Capitalize first word and proper nouns. No period at end of title. If subject is completely unidentifiable, then use, "Unknown"',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   True,
        },
        'mets_func':  mets_title,
        'default':    '',
    },
    {
        'name':       'description',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:abstract",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Description',
            'help_text':  'A caption describing the content and/or subject of the object.	Brief free text following basic Chicago Manual style guidelines.',
            'max_length': 255,
            'widget':     forms.Textarea,
            'initial':    '',
            'required':   False,
        },
        'mets_func':  _mets_simple,
        'default':    '',
    },
    {
        'name':       'creation',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:originInfo/mods:dateCreated",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Date (Created)',
            'help_text':  'Date of original creation. Not the digitization date. M/D/YYYY. If exact date is not known, then use circa ("c. 1931") or if applicable, a date range ("1930-1940").',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   False,
        },
        'prep_func':  prepare_creation,
        'proc_func':  process_creation,
        'default':    '',
    },
    {
        'name':       'location',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:originInfo/mods:place/mods:placeTerm[@type='text']",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
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
        'form_type':  forms.CharField,
        'form': {
            'label':      'Creator',
            'help_text':  'For photographs, the name of the photographer. For letters, documents and other written materials, the name of the author. For newspapers, magazine and other printed matter, the name of the publisher.	For individuals, "LastName, FirstName: CreatorRole" (e.g., "Adams, Ansel:photographer"). Multiple creators are allowed, but must be separated using a semi-colon.',
            'max_length': 255,
            'widget':     forms.Textarea,
            'initial':    '',
            'required':   False,
        },
        'prep_func':  prepare_creators,
        'proc_func':  process_creators,
        'mets_func':  mets_creators,
        'default':    '',
    },
    {
        'name':       'language',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:language/mods:languageTerm",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.ChoiceField,
        'form': {
            'label':      'Language',
            'help_text':  '',
            'choices':  LANGUAGE_CHOICES,
            'widget':     '',
            'initial':    '',
            'required':   False,
        },
        'prep_func':  prepare_language,
        'proc_func':  process_language,
        'mets_func':  mets_language,
        'default':    '',
    },
    {
        'name':       'genre',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:genre",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.ChoiceField,
        'form': {
            'label':      'Object Genre',
            'help_text':  'The genre, form, and/or physical characteristics of the object.	Use the Library of Congress Basic Genre Terms for Cultural Heritage Materials controlled vocabulary list. See Appendix E: Controlled Vocabularies or the Library of Congress website: http://memory.loc.gov/ammem/techdocs/genre.html',
            'choices': GENRE_CHOICES,
            'widget':     '',
            'initial':    '',
            'required':   False,
        },
        'mets_func':  _mets_simple,
        'default':    '',
    },
    {
        'name':       'format',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:typeOfResource",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.ChoiceField,
        'form': {
            'label':      'Object Format',
            'help_text':  'A descriptor for indicating the type of object.	Use the Densho Object Type Controlled Vocabulary List found in Appendix E: Controlled Vocabularies.',
            'choices': FORMAT_CHOICES,
            'widget':     '',
            'initial':    '',
            'required':   True,
        },
        'mets_func':  _mets_simple,
        'default':    '',
    },
    {
        'name':       'dimensions',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:physicalDescription/mods:extent",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Physical Dimensions',
            'help_text':  'The size of the original physical object. Width in inches, followed by height in inches, in the following format: "5.25W x 3.5H". For photographs, do not include border, mounts and/or frames.',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   True,
        },
        'mets_func':  _mets_simple,
        'default':    '',
    },
    {
        'name':       'organization',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:location/mods:physicalLocation",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Contributing Institution',
            'help_text':  'Name of the organization that owns the physical materials. Will probably be the name of the partner, unless materials were borrowed from external institution for scanning.',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   True,
        },
        'mets_func':  _mets_simple,
        'default':    '',
    },
    {
        'name':       'organization_id',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:location/mods:holdingExternal/mods:institutionIdentifier/mods:value",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
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
        'form_type':  forms.CharField,
        'form': {
            'label':      'Digitizer',
            'help_text':  'Name of person who created the scan. LastName, FirstName',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   True,
        },
        'default':    '',
    },
    {
        'name':       'digitize_organization',
        'xpath':      '',
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Digitizing Institution',
            'help_text':  'Name of organization responsible for scanning. Will probably be the name of the partner.',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   True,
        },
        'default':    '',
    },
    {
        'name':       'digitize_date',
        'xpath':      '',
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.DateField,
        'form': {
            'label':      'Digitize Date',
            'help_text':  'Date of scan. M/D/YYYY.',
            'widget':     '',
            'initial':    '',
            'required':   True,
        },
        'default':    '',
    },
    # technical
    {
        'name':       'credit',
        'xpath':      '',
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
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
        'form_type':  forms.CharField,
        'form': {
            'label':      'Rights and Restrictions',
            'help_text':  'Short statement about usage limitations and intellectual property for the individual object. Only needs to be filled out if the individual object has restrictions different than those of the parent collection.',
            'widget':     forms.Textarea,
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
        'form_type':  forms.CharField,
        'form': {
            'label':      'Topic',
            'help_text':  'Thematic content of object.	From Densho topics controlled vocabulary. Separate multiple topics with semi-colon.',
            'widget':     forms.Textarea,
            'initial':    '',
            'required':   False,
        },
        'prep_func':  prepare_topics,
        'proc_func':  process_topics,
        'mets_func':  mets_topics,
        'default':    '',
    },
    {
        'name':       'persons',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:subject[@ID='persons']",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Person/Organization',
            'help_text':  'People and/or organizations that are represented in the object.	For people: LastName, FirstName. Separate multiple entries with semi-colon.',
            'widget':     forms.Textarea,
            'initial':    '',
            'required':   False,
        },
        'prep_func':  prepare_persons,
        'proc_func':  process_persons,
        'mets_func':  mets_persons,
        'default':    '',
    },
    {
        'name':       'facility',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:subject/mods:geographic",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Facility',
            'help_text':  'Confinement site associated with the content of the object. From controlled vocabulary. Separate multiple entries with semi-colon.',
            'widget':     forms.Textarea,
            'initial':    '',
            'required':   False,
        },
        'prep_func':  prepare_facility,
        'proc_func':  process_facility,
        'default':    '',
    },
    {
        'name':       'notes',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:note/",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Notes',
            'help_text':  '',
            'widget':     forms.Textarea,
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
