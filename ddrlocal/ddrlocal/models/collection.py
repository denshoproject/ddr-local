from datetime import datetime, date
import json
import logging
logger = logging.getLogger(__name__)

from lxml import etree



DEFAULT_PERMISSION_COLLECTION = 1
DEFAULT_RIGHTS_COLLECTION = 'cc'

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

COLLECTION_FIELDS = [
    {
        'name':       'id',
        'group':      '',
        'xpath':      "",
        'xpath_dup':  ['/ead/archdesc/did/unitid',],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Collection ID',
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
        'group':      '',
        'xpath':      "",
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
        'group':      '',
        'xpath':      "",
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
            'help_text':  'If set to private, the permission will apply to all objects and files under this collection.',
            'widget':     '',
            'choices':    PERMISSIONS_CHOICES,
            'initial':    DEFAULT_PERMISSION_COLLECTION,
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
            'help_text':  'Setting will determine the initial default for objects in this collection.',
            'widget':     '',
            'choices':    RIGHTS_CHOICES,
            'initial':    DEFAULT_RIGHTS_COLLECTION,
            'required':   True,
        },
        'default':    '',
    },
    # overview ---------------------------------------------------------
    {
        'name':       'title',
        'group':      'overview',
        'xpath':      '/ead/eadheader/filedesc/titlestmt/titleproper',
        'xpath_dup':  ['/ead/archdesc/did/unittitle',],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Title',
            'help_text':  'The title of the collection.	Follow basic Chicago Manual Style for titles. No period.',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   True,
        },
        'default':    '',
    },
    {
        'name':       'unitdateinclusive',
        'group':      'overview',
        'xpath':      "/ead/archdesc/did/unitdate[@type='inclusive']",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Inclusive Dates',
            'help_text':  'The date range of the oldest materials and the newest materials in the collection.	Use the years separated by a dash: YYYY-YYYY. If exact dates are unknown use circa (c.).',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   True,
        },
        'default':    '',
    },
    {
        'name':       'unitdatebulk',
        'group':      'overview',
        'xpath':      "/ead/archdesc/did/unitdate[@type='bulk']",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Bulk Dates',
            'help_text':  'The date or date range of the majority of the materials in the collection.	Use the years separated by a dash: YYYY-YYYY. If exact dates are unknown use circa (c.). Can be the same as the inclusive dates if there are no predominant dates.',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   True,
        },
        'default':    '',
    },
    {
        'name':       'creators',
        'group':      'overview',
        'xpath':      "/ead/archdesc/did/origination",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Creator',
            'help_text':  'The name of the person/people/organization responsible for the creation and/or assembly of the majority of materials in the collection.	For individuals, "LastName, FirstName" (e.g. Adams, Ansel). Multiple creators are allowed but must be separated using a semi-colon.',
            'max_length': 255,
            'widget':     'Textarea',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    {
        'name':       'extent',
        'group':      'overview',
        'xpath':      "/ead/archdesc/did/physdesc/extent",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Physical Description',
            'help_text':  'A statement about the extent of the collection.',
            'max_length': 255,
            'widget':     'Textarea',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    {
        'name':       'language',
        'group':      'overview',
        'xpath':      "/ead/archdesc/did/langmaterial/language/@langcode",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'MultipleChoiceField',
        'form': {
            'label':      'Language',
            'help_text':  'The language that predominates in the original material being described.	Only needed for objects containing textual content (i.e. caption on a photograph, text of a letter). Use the Library of Congress Codes for the Representation of Names of Languages ISO 639-2 Codes (found here http://www.loc.gov/standards/iso639-2/php/code_list.php).',
            'choices':  LANGUAGE_CHOICES,
            'widget':     '',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    {
        'name':       'organization',
        'group':      'overview',
        'xpath':      "/ead/archdesc/did/repository",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Contributing Institution',
            'help_text':  "The name of the organization that owns the physical materials. In many cases this will be the partner's name unless the materials were borrowed from a different organization for scanning.",
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   True,
        },
        'default':    '',
    },
    {
        'name':       'description',
        'group':      'overview',
        'xpath':      "/ead/archdesc/did/abstract",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Abstract',
            'help_text':  'A brief statement about the creator and the scope of the collection.	Brief free text following basic Chicago Manual style guidelines.',
            'widget':     'Textarea',
            'initial':    '',
            'required':   True,
        },
        'default':    '',
    },
    {
        'name':       'notes',
        'group':      'overview',
        'xpath':      "/ead/archdesc/did/note",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Notes',
            'help_text':  'Additional information about the collection that is not appropriate for any other element.',
            'widget':     'Textarea',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    {
        'name':       'physloc',
        'group':      'overview',
        'xpath':      "/ead/archdesc/did/physloc",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Physical Location',
            'help_text':  'The place where the collection is stored.	Could be the name of a building, shelf location, etc.',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    # administative ----------------------------------------------------
    {
        'name':       'acqinfo',
        'group':      'administative',
        'xpath':      "/ead/descgrp/acqinfo",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Acquisition Information',
            'help_text':  'Information about how the collection was acquired.',
            'widget':     'Textarea',
            'initial':    '',
            'required':   True,
        },
        'default':    '',
    },
    {
        'name':       'custodhist',
        'group':      'administative',
        'xpath':      "/ead/descgrp/custodhist",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Custodial History',
            'help_text':  'Information about the provenance of the collection.',
            'widget':     'Textarea',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    {
        'name':       'accruals',
        'group':      'administative',
        'xpath':      "/ead/descgrp/accruals",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Accruals',
            'help_text':  'Can be used to note if there were multiple donations made at different times or if additional materials are expected in the future.',
            'widget':     'Textarea',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    {
        'name':       'processinfo',
        'group':      'administative',
        'xpath':      "/ead/descgrp/processinfo",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Processing Information',
            'help_text':  'Information about accessioning, arranging, describing, preserving, storing, or otherwise preparing the described materials for research use.	Free text field. Can include information about who processed the collection, who created/if there is a finding aid, deaccessioning, etc.',
            'widget':     'Textarea',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    {
        'name':       'accessrestrict',
        'group':      'administative',
        'xpath':      "/ead/descgrp/accessrestrict",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Restrictions on Access',
            'help_text':  'Information about any restrictions on access to the original physical materials.',
            'widget':     'Textarea',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    {
        'name':       'userrestrict',
        'group':      'administative',
        'xpath':      "/ead/descgrp/userrestrict",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Restrictions on Use',
            'help_text':  'Short statement about usage limitations and intellectual property for the individual object.',
            'widget':     'Textarea',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    {
        'name':       'prefercite',
        'group':      'administative',
        'xpath':      "/ead/descgrp/prefercite",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Preferred Citation',
            'help_text':  'Short courtesy text relating to the use of the object. Could identify either the collection contributor and/or donor depending on the deed of gift or usage agreement. Always begins with "Courtesy of . . ."',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   True,
        },
        'default':    '',
    },
    # bioghist ---------------------------------------------------------
    {
        'name':       'bioghist',
        'group':      'bioghist',
        'xpath':      "/ead/bioghist",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Biography and History',
            'help_text':  'Provides contextual information about the collection. Often includes information about the creator(s) and/or time period.',
            'widget':     'Textarea',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    # scopecontent -----------------------------------------------------
    {
        'name':       'scopecontent',
        'group':      'scopecontent',
        'xpath':      "/ead/scopecontent",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Scope and Content',
            'help_text':  'Summarizes the characteristics of the materials, the functions and activities that produced them, and the types of information contained in them.',
            'widget':     'Textarea',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    # related ----------------------------------------------------------
    {
        'name':       'relatedmaterial',
        'group':      'related',
        'xpath':      "/ead/relatedmaterial",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Related Materials',
            'help_text':  'Information about materials in other collections that might be of interest to researchers. Free text field. The addition of links will be available in the future.',
            'widget':     'Textarea',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    {
        'name':       'separatedmaterial',
        'group':      'related',
        'xpath':      "/ead/separatedmaterial",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Separated Materials',
            'help_text':  'Information about materials that were pulled from this collection and added to another. Free text field. The addition of links will be available in the future.',
            'widget':     'Textarea',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },

]



# display_* --- Display functions --------------------------------------
#
# These functions take Python data from the corresponding Collection field
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

# title

def display_creators( data ):
    lines = []
    if type(data) != type([]):
        data = data.split(';')
    for l in data:
        lines.append({'person': l.strip()})
    return _render_multiline_dict('<a href="{person}">{person}</a>', lines)

# extent

def display_language( data ):
    labels = []
    for c in LANGUAGE_CHOICES:
        if c[0] in data:
            labels.append(c[1])
    if labels:
        return ', '.join(labels)
    return ''

# organization
# description
# notes
# physloc
#
# acqinfo
# custodhist
# accruals
# processinfo
# accessrestrict
# userrestrict
# prefercite
#
# bioghist
#
# scopecontent
#
# relatedmaterial
# separatedmaterial

# The following are utility functions used by display_* functions.

def _render_multiline_dict( template, data ):
    t = []
    for x in data:
        if type(x) == type({}):
            t.append(template.format(**x))
        else:
            t.append(x)
    return '\n'.join(t)



# formprep_* --- Form pre-processing functions.--------------------------
#
# These functions take Python data from the corresponding Collection field
# and format it so that it can be used in an HTML form.
#

# id
# created
# lastmod
# public
# title
# creators
# extent
# language
# organization
# description
# notes
# physloc
#
# acqinfo
# custodhist
# accruals
# processinfo
# accessrestrict
# userrestrict
# prefercite
#
# bioghist
#
# scopecontent
#
# relatedmaterial
# separatedmaterial

# The following are utility functions used by formprep_* functions.

def _formprep_basic(data):
    if data:
        return json.dumps(data)
    return ''



# formpost_* --- Form post-processing functions ------------------------
#
# These functions take data from the corresponding form field and turn it
# into Python objects that are inserted into the Collection.
#

# id
# created
# lastmod
# public
# title
# unitdate_inclusive
# unitdate_bulk
# creators
# extent
# language
# organization
# description
# notes
# physloc
#
# acqinfo
# custodhist
# accruals
# processinfo
# accessrestrict
# userrestrict
# prefercite
#
# bioghist
#
# scopecontent
#
# relatedmaterial
# separatedmaterial

# The following are utility functions used by formpost_* functions.

def _formpost_basic(data):
    if data:
        try:
            return json.loads(data)
        except:
            return data
    return ''



# ead_* --- EAD XML export functions -----------------------------------
#
# These functions take Python data from the corresponding Collection field
# and write it to a EAD XML document.
#

def ead_id(tree, namespaces, field, value):
    tree = _set_tag_text(tree, namespaces, "/ead/eadheader/eadid", value)
    tree = _set_tag_text(tree, namespaces, "/ead/archdesc/did/unitid", value)
    return tree

def ead_created(tree, namespaces, field, value):
    return _set_attr(tree, namespaces, "/ead/eadheader/eadid", "created", value.strftime(DATETIME_FORMAT))

def ead_lastmod(tree, namespaces, field, value):
    return _set_attr(tree, namespaces, "/ead/eadheader/eadid", "lastmod", value.strftime(DATETIME_FORMAT))

# public

def ead_title(tree, namespaces, field, value):
    tree = _set_tag_text(tree, namespaces, "/ead/eadheader/filedesc/titlestmt/titleproper", value)
    tree = _set_tag_text(tree, namespaces, "/ead/archdesc/did/unittitle", value)
    return tree

# unitdate_inclusive
# unitdate_bulk
# creators
# extent

#def ead_language(tree, namespaces, field, value):
#    code = value
#    label = ''
#    for l in LANGUAGE_CHOICES:
#        if l[0] == code:
#            label = l[1]
#    tree = _set_attr(tree, namespaces, "/ead/eadheader/profiledesc/langusage/language", "langcode", code)
#    tree = _set_tag_text(tree, namespaces, "/ead/eadheader/profiledesc/langusage/language", label)
#    tree = _set_attr(tree, namespaces, "/ead/archdesc/did/langmaterial/language", "langcode", code)
#    tree = _set_tag_text(tree, namespaces, "/ead/archdesc/did/langmaterial/language", label)
#    return tree

# organization
# description
# notes
# physloc
#
# acqinfo
# custodhist
# accruals
# processinfo
# accessrestrict
# userrestrict
# prefercite
#
# bioghist
#
# scopecontent
#
# relatedmaterial
# separatedmaterial

# The following are utility functions used by ead_* functions.

def _expand_attrib_namespace(attr, namespaces):
    ns,a = attr.split(':')
    return '{%s}%s' % (namespaces[ns], a)

def _getval(tree, namespaces, xpath):
    """Gets the first value; yes this is probably suboptimal
    """
    val = None
    vals = tree.xpath(xpath, namespaces=namespaces)
    if vals:
        val = vals[0]
    return val

def _set_attr(tree, namespaces, xpath, attr, value):
    tags = tree.xpath(xpath, namespaces=namespaces)
    if tags:
        tag = tags[0]
        tag.set(attr, value)
    return tree

def _set_tag_text(tree, namespaces, xpath, value):
    tag = _getval(tree, namespaces, xpath)
    if tag and value:
        tag.text = value
    return tree

def _duplicate(tree, namespaces, src_xpath, dest_xpath):
    i = tree.xpath( src_xpath,  namespaces=namespaces )[0]
    tag = tree.xpath( dest_xpath, namespaces=namespaces )[0]
    tag.text = i
    return tree

def _ead_simple(tree, namespaces, field, value):
    return _set_tag_text(tree, namespaces, field['xpath'], value)



# XML grow functions ---------------------------------------------------
# Add tags to XML if not found in xpath

def _find_existing_ancestor(tree, xpath):
    frag = xpath
    while not tree.xpath(frag):
        frag = frag.rsplit('/', 1)[0]
    return frag

def _next_tag(frag, xpath):
    ftags = frag.split('/')
    xtags = xpath.split('/')
    last = xtags.pop()
    while xtags != ftags:
        last = xtags.pop()
    return last

def _graft(tree, frag, tag):
    if ('@' not in tag):
        parent = tree.xpath(frag)[0]
        t = etree.Element(tag)
        parent.append(t)

def _grow(tree, xpath):
    """
    THIS needs to be aware of attrib
    """
    frag = _find_existing_ancestor(tree, xpath)
    while frag != xpath:
        tag = _next_tag(frag, xpath)
        _graft(tree, frag, tag)
        frag = _find_existing_ancestor(tree, xpath)

def _mktagp(tree, COLLECTION_FIELDS):
    """If tags specified in xpaths don't exist, make 'em.
    """
    for f in COLLECTION_FIELDS:
        x = f['xpath']
        if x:
            something = tree.xpath(x)
            if ('@' not in x) and (not something):
                _grow(tree, x)

"""
from lxml import etree
from ddrlocal.models import collection
from ddrlocal.models.collection import COLLECTION_FIELDS
p = '/media/WD5000BMV-2/ddr/ddr-testing-61/ead.xml'
with open(p, 'rw') as f:
    xml0 = f.read()

print(xml0)
tree = etree.fromstring(xml0)
collection._mktagp(tree, COLLECTION_FIELDS)
xml1 = etree.tostring(tree, pretty_print=True)
print(xml1)
with open(p, 'w') as f:
    f.write(xml1)
"""
