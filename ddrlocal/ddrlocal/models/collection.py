from datetime import datetime, date
import json
import os

from lxml import etree

from django import forms
from django.conf import settings
from django.core.urlresolvers import reverse

from DDR.models import DDRCollection
from ddrlocal.models.entity import DDRLocalEntity
from ddrlocal import VERSION, git_commit



LANGUAGE_CHOICES = [['eng','English'],
                    ['jpn','Japanese'],
                    ['esp','Spanish'],]



class DDRLocalCollection( DDRCollection ):
    """
    This subclass of Entity and DDREntity adds functions for reading and writing
    entity.json, and preparing/processing Django forms.
    """
    id = 'whatever'
    repo = None
    org = None
    cid = None

    def __init__(self, *args, **kwargs):
        super(DDRLocalCollection, self).__init__(*args, **kwargs)
        self.id = self.uid
        self.repo = self.id.split('-')[0]
        self.org = self.id.split('-')[1]
        self.cid = self.id.split('-')[2]
    
    def __repr__(self):
        return "<DDRLocalCollection %s>" % (self.id)
    
    def url( self ):
        return reverse('webui-collection', args=[self.repo, self.org, self.cid])
    
    @staticmethod
    def collection_path(request, repo, org, cid):
        return os.path.join(settings.MEDIA_BASE, '{}-{}-{}'.format(repo, org, cid))
    
    @staticmethod
    def create(path):
        """Creates a new collection with the specified collection ID.
        @param path: Absolute path to collection; must end in valid DDR collection id.
        """
        collection = Collection(path)
        for f in EAD_FIELDS:
            if hasattr(f, 'name') and hasattr(f, 'initial'):
                setattr(collection, f['name'], f['initial'])
        return collection
    
    def entities( self ):
        """Returns relative paths to entities."""
        entities = []
        if os.path.exists(self.files_path):
            for eid in os.listdir(self.files_path):
                path = os.path.join(self.files_path, eid)
                entity = DDRLocalEntity.from_json(path)
                for lv in entity.labels_values():
                    if lv['label'] == 'title':
                        entity.title = lv['value']
                entities.append(entity)
        return entities
    
    def labels_values(self):
        """Generic display
        """
        lv = []
        for f in EAD_FIELDS:
            if hasattr(self, f['name']) and f.get('form',None):
                item = {'label': f['form']['label'],
                        'value': getattr(self, f['name'])}
                lv.append(item)
        return lv
    
    def form_data(self):
        """Prep data dict to pass into CollectionForm object.
        
        Certain fields may require special processing, which will be performed
        by the function specified in field['prep_func'].
        
        @returns data: dict object as used by Django Form object.
        """
        data = {}
        for f in EAD_FIELDS:
            if hasattr(self, f['name']) and f.get('form',None):
                key = f['name']
                value = getattr(self, f['name'])
                # hand off special processing to function specified in EAD_FIELDS
                if f.get('prep_func',None):
                    func = f['prep_func']
                    value = func(value)
                # end special processing
                data[key] = value
        return data
    
    def form_process(self, form):
        """Process cleaned_data coming from CollectionForm
        
        Certain fields may require special processing, which will be performed
        by the function specified in field['proc_func'].
        
        @param form
        """
        for f in EAD_FIELDS:
            if hasattr(self, f['name']) and f.get('form',None):
                key = f['name']
                cleaned_data = form.cleaned_data[key]
                # hand off special processing to function specified in EAD_FIELDS
                if f.get('proc_func',None):
                    func = f['proc_func']
                    cleaned_data = func(cleaned_data)
                # end special processing
                setattr(self, key, cleaned_data)
        # update lastmod
        self.lastmod = datetime.now()
    
    @staticmethod
    def from_json(collection_abs):
        collection = DDRLocalCollection(collection_abs)
        collection_uid = collection.id  # save this just in case
        collection.load_json(collection.json_path)
        if not collection.id:
            # id gets overwritten if collection.json is blank
            collection.id = collection_uid
        return collection
    
    def load_json(self, path):
        """Populate Collection data from .json file.
        @param path: Absolute path to collection directory
        """
        json_data = self.json().data
        for ff in EAD_FIELDS:
            for f in json_data:
                if f.keys()[0] == ff['name']:
                    setattr(self, f.keys()[0], f.values()[0])
        # special cases
        if self.created:
            self.created = datetime.strptime(self.created, settings.DATETIME_FORMAT)
        else:
            self.created = datetime.now()
        if self.lastmod:
            self.lastmod = datetime.strptime(self.lastmod, settings.DATETIME_FORMAT)
        else:
            self.lastmod = datetime.now()
        # end special cases
        # Ensure that every field in EAD_FIELDS is represented
        # even if not present in json_data.
        for ff in EAD_FIELDS:
            if not hasattr(self, ff['name']):
                setattr(self, ff['name'], ff.get('default',None))
    
    def dump_json(self):
        """Dump Collection data to .json file.
        @param path: Absolute path to .json file.
        """
        collection = [{'application': 'https://github.com/densho/ddr-local.git',
                       'commit': git_commit(),
                       'release': VERSION,}]
        for ff in EAD_FIELDS:
            item = {}
            key = ff['name']
            val = ''
            if hasattr(self, ff['name']):
                val = getattr(self, ff['name'])
                # special cases
                if key in ['created', 'lastmod']:
                    val = val.strftime(settings.DATETIME_FORMAT)
                elif key in ['digitize_date']:
                    val = val.strftime(settings.DATE_FORMAT)
                # end special cases
            item[key] = val
            collection.append(item)
        json_pretty = json.dumps(collection, indent=4, separators=(',', ': '))
        with open(self.json_path, 'w') as f:
            f.write(json_pretty)
    
    def dump_ead(self):
        """Dump Collection data to ead.xml file.
        """
        NAMESPACES = None
        tree = etree.fromstring(self.ead().xml)
        for f in EAD_FIELDS:
            key = f['name']
            value = ''
            if hasattr(self, f['name']):
                value = getattr(self, f['name'])
                # hand off special processing to function specified in EAD_FIELDS
                if f.get('ead_func',None):
                    func = f['ead_func']
                    tree = func(tree, NAMESPACES, f, value)
                # end special processing
        xml_pretty = etree.tostring(tree, pretty_print=True)
        with open(self.ead_path, 'w') as f:
            f.write(xml_pretty)



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

def _mktagp(tree, EAD_FIELDS):
    """If tags specified in xpaths don't exist, make 'em.
    """
    for f in EAD_FIELDS:
        x = f['xpath']
        if x:
            something = tree.xpath(x)
            if ('@' not in x) and (not something):
                _grow(tree, x)

"""
from lxml import etree
from ddrlocal.models import collection
from ddrlocal.models.collection import EAD_FIELDS
p = '/media/WD5000BMV-2/ddr/ddr-testing-61/ead.xml'
with open(p, 'rw') as f:
    xml0 = f.read()

print(xml0)
tree = etree.fromstring(xml0)
collection._mktagp(tree, EAD_FIELDS)
xml1 = etree.tostring(tree, pretty_print=True)
print(xml1)
with open(p, 'w') as f:
    f.write(xml1)
"""



# forms pre-processing functions ---------------------------------------
# convert from Python objects to form(data)

def _prepare_basic(data):
    if data:
        return json.dumps(data)
    return ''

# id
# created
# lastmod
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

def _ead_simple(tree, namespaces, field, value):
    return _set_tag_text(tree, namespaces, field['xpath'], value)

# - - - - - - - - - - - - - - - -

def ead_id(tree, namespaces, field, value):
    tree = _set_tag_text(tree, namespaces, "/ead/eadheader/eadid", value)
    tree = _set_tag_text(tree, namespaces, "/ead/archdesc/did/unitid", value)
    return tree

def ead_created(tree, namespaces, field, value):
    return _set_attr(tree, namespaces, "/ead/eadheader/eadid", "created", value.strftime(settings.DATETIME_FORMAT))

def ead_lastmod(tree, namespaces, field, value):
    return _set_attr(tree, namespaces, "/ead/eadheader/eadid", "lastmod", value.strftime(settings.DATETIME_FORMAT))

def ead_title(tree, namespaces, field, value):
    tree = _set_tag_text(tree, namespaces, "/ead/eadheader/filedesc/titlestmt/titleproper", value)
    tree = _set_tag_text(tree, namespaces, "/ead/archdesc/did/unittitle", value)
    return tree

# unitdate_inclusive
# unitdate_bulk
# creators
# extent

def ead_language(tree, namespaces, field, value):
    code = value
    label = ''
    for l in LANGUAGE_CHOICES:
        if l[0] == code:
            label = l[1]
    tree = _set_attr(tree, namespaces, "/ead/eadheader/profiledesc/langusage/language", "langcode", code)
    tree = _set_tag_text(tree, namespaces, "/ead/eadheader/profiledesc/langusage/language", label)
    tree = _set_attr(tree, namespaces, "/ead/archdesc/did/langmaterial/language", "langcode", code)
    tree = _set_tag_text(tree, namespaces, "/ead/archdesc/did/langmaterial/language", label)
    return tree

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



# ----------------------------------------------------------------------

EAD_FIELDS = [
    {
        'name':       'id',
        'group':      '',
        'xpath':      "",
        'xpath_dup':  ['/ead/archdesc/did/unitid',],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Collection ID',
            'help_text':  '',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   True,
        },
        'ead_func':   ead_id,
        'default':    '',
    },
    {
        'name':       'created',
        'group':      '',
        'xpath':      "",
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
        'ead_func':   ead_created,
        'default':    '',
    },
    {
        'name':       'lastmod',
        'group':      '',
        'xpath':      "",
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
        'ead_func':   ead_lastmod,
        'default':    '',
    },
    # overview ---------------------------------------------------------
    {
        'name':       'title',
        'group':      'overview',
        'xpath':      '/ead/eadheader/filedesc/titlestmt/titleproper',
        'xpath_dup':  ['/ead/archdesc/did/unittitle',],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Title',
            'help_text':  'The title of the collection.	Follow basic Chicago Manual Style for titles. No period.',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   True,
        },
        'ead_func':   ead_title,
        'default':    '',
    },
    {
        'name':       'unitdateinclusive',
        'group':      'overview',
        'xpath':      "/ead/archdesc/did/unitdate[@type='inclusive']",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Inclusive Dates',
            'help_text':  'The date range of the oldest materials and the newest materials in the collection.	Use the years separated by a dash: YYYY-YYYY. If exact dates are unknown use circa (c.).',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   True,
        },
        'ead_func':   _ead_simple,
        'default':    '',
    },
    {
        'name':       'unitdatebulk',
        'group':      'overview',
        'xpath':      "/ead/archdesc/did/unitdate[@type='bulk']",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Bulk Dates',
            'help_text':  'The date or date range of the majority of the materials in the collection.	Use the years separated by a dash: YYYY-YYYY. If exact dates are unknown use circa (c.). Can be the same as the inclusive dates if there are no predominant dates.',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   True,
        },
        'ead_func':   _ead_simple,
        'default':    '',
    },
    {
        'name':       'creators',
        'group':      'overview',
        'xpath':      "/ead/archdesc/did/origination",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Creator',
            'help_text':  'The name of the person/people/organization responsible for the creation and/or assembly of the majority of materials in the collection.	For individuals, "LastName, FirstName" (e.g. Adams, Ansel). Multiple creators are allowed but must be separated using a semi-colon.',
            'max_length': 255,
            'widget':     forms.Textarea,
            'initial':    '',
            'required':   False,
        },
        'ead_func':   _ead_simple,
        'default':    '',
    },
    {
        'name':       'extent',
        'group':      'overview',
        'xpath':      "/ead/archdesc/did/physdesc/extent",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Physical Description',
            'help_text':  'A statement about the extent of the collection.',
            'max_length': 255,
            'widget':     forms.Textarea,
            'initial':    '',
            'required':   False,
        },
        'ead_func':   _ead_simple,
        'default':    '',
    },
    {
        'name':       'language',
        'group':      'overview',
        'xpath':      "/ead/archdesc/did/langmaterial/language/@langcode",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.ChoiceField,
        'form': {
            'label':      'Language',
            'help_text':  'The language that predominates in the original material being described.	Only needed for objects containing textual content (i.e. caption on a photograph, text of a letter). Use the Library of Congress Codes for the Representation of Names of Languages ISO 639-2 Codes (found here http://www.loc.gov/standards/iso639-2/php/code_list.php).',
            'choices':  LANGUAGE_CHOICES,
            'widget':     '',
            'initial':    '',
            'required':   False,
        },
        'ead_func':   ead_language,
        'default':    '',
    },
    {
        'name':       'organization',
        'group':      'overview',
        'xpath':      "/ead/archdesc/did/repository",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Contributing Institution',
            'help_text':  "The name of the organization that owns the physical materials. In many cases this will be the partner's name unless the materials were borrowed from a different organization for scanning.",
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   True,
        },
        'ead_func':   _ead_simple,
        'default':    '',
    },
    {
        'name':       'description',
        'group':      'overview',
        'xpath':      "/ead/archdesc/did/abstract",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Abstract',
            'help_text':  'A brief statement about the creator and the scope of the collection.	Brief free text following basic Chicago Manual style guidelines.',
            'widget':     forms.Textarea,
            'initial':    '',
            'required':   True,
        },
        'ead_func':   _ead_simple,
        'default':    '',
    },
    {
        'name':       'notes',
        'group':      'overview',
        'xpath':      "/ead/archdesc/did/note",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Notes',
            'help_text':  'Additional information about the collection that is not appropriate for any other element.',
            'widget':     forms.Textarea,
            'initial':    '',
            'required':   False,
        },
        'ead_func':   _ead_simple,
        'default':    '',
    },
    {
        'name':       'physloc',
        'group':      'overview',
        'xpath':      "/ead/archdesc/did/physloc",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Physical Location',
            'help_text':  'The place where the collection is stored.	Could be the name of a building, shelf location, etc.',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   False,
        },
        'ead_func':   _ead_simple,
        'default':    '',
    },
    # administative ----------------------------------------------------
    {
        'name':       'acqinfo',
        'group':      'administative',
        'xpath':      "/ead/descgrp/acqinfo",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Acquisition Information',
            'help_text':  'Information about how the collection was acquired.',
            'widget':     forms.Textarea,
            'initial':    '',
            'required':   True,
        },
        'ead_func':   _ead_simple,
        'default':    '',
    },
    {
        'name':       'custodhist',
        'group':      'administative',
        'xpath':      "/ead/descgrp/custodhist",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Custodial History',
            'help_text':  'Information about the provenance of the collection.',
            'widget':     forms.Textarea,
            'initial':    '',
            'required':   False,
        },
        'ead_func':   _ead_simple,
        'default':    '',
    },
    {
        'name':       'accruals',
        'group':      'administative',
        'xpath':      "/ead/descgrp/accruals",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Accruals',
            'help_text':  'Can be used to note if there were multiple donations made at different times or if additional materials are expected in the future.',
            'widget':     forms.Textarea,
            'initial':    '',
            'required':   False,
        },
        'ead_func':   _ead_simple,
        'default':    '',
    },
    {
        'name':       'processinfo',
        'group':      'administative',
        'xpath':      "/ead/descgrp/processinfo",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Processing Information',
            'help_text':  'Information about accessioning, arranging, describing, preserving, storing, or otherwise preparing the described materials for research use.	Free text field. Can include information about who processed the collection, who created/if there is a finding aid, deaccessioning, etc.',
            'widget':     forms.Textarea,
            'initial':    '',
            'required':   False,
        },
        'ead_func':   _ead_simple,
        'default':    '',
    },
    {
        'name':       'accessrestrict',
        'group':      'administative',
        'xpath':      "/ead/descgrp/accessrestrict",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Restrictions on Access',
            'help_text':  'Information about any restrictions on access to the original physical materials.',
            'widget':     forms.Textarea,
            'initial':    '',
            'required':   False,
        },
        'ead_func':   _ead_simple,
        'default':    '',
    },
    {
        'name':       'userrestrict',
        'group':      'administative',
        'xpath':      "/ead/descgrp/userrestrict",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Restrictions on Use',
            'help_text':  'Short statement about usage limitations and intellectual property for the individual object.',
            'widget':     forms.Textarea,
            'initial':    '',
            'required':   False,
        },
        'ead_func':   _ead_simple,
        'default':    '',
    },
    {
        'name':       'prefercite',
        'group':      'administative',
        'xpath':      "/ead/descgrp/prefercite",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Preferred Citation',
            'help_text':  'Short courtesy text relating to the use of the object. Could identify either the collection contributor and/or donor depending on the deed of gift or usage agreement. Always begins with "Courtesy of . . ."',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   True,
        },
        'ead_func':   _ead_simple,
        'default':    '',
    },
    # bioghist ---------------------------------------------------------
    {
        'name':       'bioghist',
        'group':      'bioghist',
        'xpath':      "/ead/bioghist",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Biography and History',
            'help_text':  'Provides contextual information about the collection. Often includes information about the creator(s) and/or time period.',
            'widget':     forms.Textarea,
            'initial':    '',
            'required':   False,
        },
        'ead_func':   _ead_simple,
        'default':    '',
    },
    # scopecontent -----------------------------------------------------
    {
        'name':       'scopecontent',
        'group':      'scopecontent',
        'xpath':      "/ead/scopecontent",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Scope and Content',
            'help_text':  'Summarizes the characteristics of the materials, the functions and activities that produced them, and the types of information contained in them.',
            'widget':     forms.Textarea,
            'initial':    '',
            'required':   False,
        },
        'ead_func':   _ead_simple,
        'default':    '',
    },
    # related ----------------------------------------------------------
    {
        'name':       'relatedmaterial',
        'group':      'related',
        'xpath':      "/ead/relatedmaterial",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Related Materials',
            'help_text':  'Information about materials in other collections that might be of interest to researchers. Free text field. The addition of links will be available in the future.',
            'widget':     forms.Textarea,
            'initial':    '',
            'required':   False,
        },
        'ead_func':   _ead_simple,
        'default':    '',
    },
    {
        'name':       'separatedmaterial',
        'group':      'related',
        'xpath':      "/ead/separatedmaterial",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Separated Materials',
            'help_text':  'Information about materials that were pulled from this collection and added to another. Free text field. The addition of links will be available in the future.',
            'widget':     forms.Textarea,
            'initial':    '',
            'required':   False,
        },
        'ead_func':   _ead_simple,
        'default':    '',
    },

]
