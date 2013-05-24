import datetime
import os
import StringIO

from lxml import etree

from django import forms

from xmlforms.forms import XMLForm


COUNTRY_CHOICES = [['us','US'],
                   ['ca','Canada'],
                   ['jp','Japan'],]

LANGUAGE_CHOICES = [['en','English'],
                    ['ja','Japanese'],
                    ['es','Spanish'],]

def repository_codes():
    return [('ddr-densho','ddr-densho'),
            ('ddr-testing','ddr-testing'),]


EAD_XML = ''
ead_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ead.xml')
with open(ead_path, 'r') as f:
    EAD_XML = f.read()



EADHEADER_FIELDS = [
    {
        'name':       'eadid',
        'xpath':      '/ead/eadheader/eadid',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':     'eadid',
            'help_text': '',
            'widget':    '',
            'initial':   '',
            'max_length': 255,
            'required': True,
        },
        'default':    '',
    },
    {
        'name':       'eadid_countrycode',
        'xpath':      '/ead/eadheader/eadid/@countrycode',
        'model_type': str,
        'form_type':  forms.ChoiceField,
        'form': {
            'label':     'Country',
            'help_text': '',
            'widget':    '',
            'choices': COUNTRY_CHOICES,
            'initial':   '',
            'required': True,
        },
        'default':    '',
    },
    {
        'name':       'eadid_identifier',
        'xpath':      '/ead/eadheader/eadid/@identifier',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':     'eadid identifier',
            'help_text': '',
            'widget':    '',
            'initial':   '',
            'max_length': 255,
            'required': True,
        },
        'default':   '',
    },
    {
        'name':       'eadid_mainagencycode',
        'xpath':      '/ead/eadheader/eadid/@mainagencycode',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':     'agency code',
            'help_text': '',
            'widget':    '',
            'initial':   '',
            'max_length': 255,
            'required': True,
        },
        'default':    '',
    },
    {
        'name':       'titlestmt_titleproper',
        'xpath':      '/ead/eadheader/filedesc/titlestmt/titleproper',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':     'Title',
            'help_text': 'The title of the collection. Follow basic Chicago Manual Style for titles. No period.',
            'widget':    '',
            'initial':   '',
            'max_length': 255,
            'required': True,
        },
        'default':    '',
    },
    {
        'name':       'titlestmt_subtitle',
        'xpath':      '/ead/eadheader/filedesc/titlestmt/subtitle',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':     'Subtitle',
            'help_text': '',
            'widget':    '',
            'initial':   '',
            'max_length': 255,
            'required': False,
        },
        'default':    '',
   },
   {
        'name':       'titlestmt_author',
        'xpath':      '/ead/eadheader/filedesc/titlestmt/author',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':     'Creator',
            'help_text': '',
            'widget':    '',
            'initial':   '',
            'max_length': 255,
            'required': True,
        },
        'default':    '',
    },
    {
        'name':       'publicationstmt_publisher',
        'xpath':      '/ead/eadheader/filedesc/publicationstmt/publisher',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':     'Publisher',
            'help_text': '',
            'widget':    '',
            'initial':   '',
            'max_length': 255,
            'required': True,
        },
        'default':    '',
    },
    {
        'name':       'publicationstmt_date',
        'xpath':      '/ead/eadheader/filedesc/publicationstmt/date/@normal',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':     'Publication Date',
            'help_text': 'YYYY',
            'widget':    '',
            'initial':   '',
            'max_length': 255,
            'required': True,
        },
        'default':    '',
    },
    {
        'name':       'profiledesc_creation',
        'xpath':      '/ead/eadheader/profiledesc/creation',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':     'Profile Creator',
            'help_text': '',
            'widget':    '',
            'initial':   '',
            'max_length': 255,
            'required': True,
        },
        'default':    '',
    },
    {
        'name':       'profiledesc_date',
        'xpath':      '/ead/eadheader/profiledesc/creation/date/@normal',
        'model_type': datetime.date,
        'form_type':  forms.DateField,
        'form': {
            'label':     'Profile Date',
            'help_text': 'YYYY-MM-DD',
            'widget':    '',
            'initial':   '',
            'required': True,
        },
        'default':    '',
    },
    {
        'name':       'langcode',
        'xpath':      '/ead/eadheader/profiledesc/langusage/language/@langcode',
        'model_type': str,
        'form_type':  forms.ChoiceField,
        'form': {
            'label':     'Language',
            'help_text': '',
            'widget':    '',
            'choices':   LANGUAGE_CHOICES,
            'initial':   '',
            'required':  True,
        },
        'default':    '',
    },
]

class EadHeaderForm(XMLForm):
    
    def __init__(self, *args, **kwargs):
        super(EadHeaderForm, self).__init__(*args, **kwargs)
    
    @staticmethod
    def process(xml, fields, form):
        """<eadheader>-specific processing
        """
        xml = XMLForm.process(xml, fields, form)
        tree = etree.parse(StringIO.StringIO(xml))
        for f in fields:
            
            # both the tag.text and @normal are YYYY
            # <eadheader><eadid><filedesc><publicationstmt>
            #   <date encodinganalog="Date" normal="1970">1970</date>
            if f['name'] == 'publicationstmt_date':
                tag      = tree.xpath( f['xpath'].split('/@')[0] )[0]
                tag.text = tree.xpath( f['xpath'] )[0]
            
            # @normal is YYYY-MM-DD, tag.text is pretty
            # <eadheader><eadid><profiledesc><creation>
            #   <date normal="1970-1-1">01 Jan 1970</date>
            if f['name'] == 'profiledesc_date':
                attr = tree.xpath( f['xpath'] )[0]
                ymd = attr.split('-')
                prettydate = datetime.date(int(ymd[0]), int(ymd[1]), int(ymd[2])).strftime('%d %b %Y')
                tag      = tree.xpath( f['xpath'].split('/@')[0] )[0]
                tag.text = prettydate
        
        return etree.tostring(tree, pretty_print=True)



ARCHDESC_FIELDS = [
    {
        'name':       'head',
        'xpath':      '/ead/archdesc/did/head',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':     'Head',
            'help_text': '',
            'widget':    '',
            'initial':   '',
            'required':  True,
        },
        'default':    'Collection Overview',
    },
    {
        'name':       'repository',
        'xpath':      '/ead/archdesc/did/repository',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Contributing Institution',
            'help_text': 'The name of the organization that owns the physical materials.  In many cases this will be the partner\'s name unless the materials were borrowed from a different organization for scanning.',
            'max_length':255,
            'widget':   '',
            'initial':  '',
            'required': True,
        },
        'default':    'Repository Name Goes Here',
    },
    {
        'name':       'archdesc_creator',
        'xpath':      '/ead/archdesc/did/origination',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Creator',
            'help_text': 'The name of the person/people/organization responsible for the creation and/or assembly of the majority of materials in the collection. For individuals, "LastName, FirstName" (e.g. Adams, Ansel). Multiple creators are allowed but must be separated using a semi-colon.',
            'max_length':255,
            'widget':   '',
            'initial':  '',
            'required': True,
        },
        'default':    'Doe, John A. (John Doe), 1911-1992',
    },
    {
        'name':       'unittitle',
        'xpath':      '/ead/archdesc/did/unittitle',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Title',
            'help_text': 'The title of the collection. Follow basic Chicago Manual Style for titles. No period.',
            'max_length':255,
            'widget':   '',
            'initial':  '',
            'required': True,
        },
        'default':    'John A. Doe Papers',
    },
#    {
#        'name':       'unitdate_inclusive',
#        'xpath':      '/ead/archdesc/did/unitdate',  attr: type="inclusive"
#        'model_type': str,
#        'form_type':  forms.CharField,
#        'form': {
#            'label':    'Inclusive Dates',
#            'help_text': 'The date range of the oldest materials and the newest materials in the collection. Use the years separated by a dash: YYYY-YYYY. If exact dates are unknown use circa (c.).',
#            'max_length':9,
#            'widget':   '',
#            'initial':  '',
#            'required': True,
#        },
#        'default':    '1940-1950',
#    },
#    {
#        'name':       'unitdate_bulk',
#        'xpath':      '/ead/archdesc/did/unitdate',  attr: type="bulk"
#        'model_type': str,
#        'form_type':  forms.CharField,
#        'form': {
#            'label':    'Bulk Dates',
#            'help_text': 'The date or date range of the majority of the materials in the collection. Use the years separated by a dash: YYYY-YYYY. If exact dates are unknown use circa (c.). Can be the same as the inclusive dates if there are no predominant dates.',
#            'max_length':9,
#            'widget':   '',
#            'initial':  '',
#            'required': True,
#        },
#        'default':    '1940-1950',
#    },
    {
        'name':       'unitid',
        'xpath':      '/ead/archdesc/did/unitid',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Collection ID',
            'help_text': 'The unique identifier for the collection.	This ID will be created using the Densho ID Service.',
            'max_length':255,
            'widget':   '',
            'initial':  '',
            'required': True,
        },
        'default':    '',
    },
    {
        'name':       'extent',
        'xpath':      '/ead/archdesc/did/physdesc/extent',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Physical Description',
            'help_text': 'A statement about the extent of the collection.',
            'max_length':255,
            'widget':   '',
            'initial':  '',
            'required': True,
        },
        'default':    'N linear ft.',
    },
    {
        'name':       'abstract',
        'xpath':      '/ead/archdesc/did/abstract',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Abstract',
            'help_text': 'A brief statement about the creator and the scope of the collection. Brief free text following basic Chicago Manual style guidelines.',
            'widget':   forms.Textarea,
            'initial':  '',
            'required': True,
        },
        'default':    '',
    },
    {
        'name':       'notes',
        'xpath':      '/ead/archdesc/did/note',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Notes',
            'help_text': 'Additional information about the collection that is not appropriate for any other element.',
            'widget':   forms.Textarea,
            'initial':  '',
            'required': False,
        },
        'default':    '',
    },
    {
        'name':       'langcode',
        'xpath':      '/ead/archdesc/did/langmaterial/language/@langcode',
        'model_type': str,
        'form_type':  forms.ChoiceField,
        'form': {
            'label':    'Language',
            'help_text': 'The language that predominates in the original material being described.	Only needed for objects containing textual content (i.e. caption on a photograph, text of a letter). Use the Library of Congress Codes for the Representation of Names of Languages ISO 639-2 Codes (found here http://www.loc.gov/standards/iso639-2/php/code_list.php).',
            'choices':  LANGUAGE_CHOICES,
            'widget':   '',
            'initial':  '',
            'required': False,
        },
        'default':    'eng',
    },
]

class ArchDescForm(XMLForm):
    
    def __init__(self, *args, **kwargs):
        super(ArchDescForm, self).__init__(*args, **kwargs)
    
    @staticmethod
    def process(xml, fields, form):
        xml = XMLForm.process(xml, fields, form)
        tree = etree.parse(StringIO.StringIO(xml))
        return etree.tostring(tree, pretty_print=True)



COLLECTION_OVERVIEW_FIELDS = [
    {
        'name':       'titleproper',
        'xpath':      '/ead/eadheader/filedesc/titlestmt/titleproper',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':     'Title',
            'help_text': 'The title of the collection. Follow basic Chicago Manual Style for titles. No period.',
            'widget':    '',
            'initial':   '',
            'max_length': 255,
            'required': True,
        },
        'default':    '',
    },
    {
        'name':       'unittitle',
        'xpath':      '/ead/archdesc/did/unittitle',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Title',
            'help_text': 'The title of the collection. Follow basic Chicago Manual Style for titles. No period.',
            'max_length':255,
            'widget':   '',
            'initial':  '',
            'required': True,
        },
        'default':    '',
    },
    {
        'name':       'unitdate_inclusive',
        'xpath':      "/ead/archdesc/did/unitdate[@type='inclusive']",
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Inclusive Dates',
            'help_text': 'The date range of the oldest materials and the newest materials in the collection. Use the years separated by a dash: YYYY-YYYY. If exact dates are unknown use circa (c.).',
            'max_length':255,
            'widget':   '',
            'initial':  '',
            'required': True,
        },
        'default':    '',
    },
    {
        'name':       'unitdate_bulk',
        'xpath':      "/ead/archdesc/did/unitdate[@type='bulk']",
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Bulk Dates',
            'help_text': 'The date or date range of the majority of the materials in the collection. Use the years separated by a dash: YYYY-YYYY. If exact dates are unknown use circa (c.). Can be the same as the inclusive dates if there are no predominant dates.',
            'max_length':255,
            'widget':   '',
            'initial':  '',
            'required': True,
        },
        'default':    '',
    },
    {
        'name':       'collectionid',
        'xpath':      '/ead/archdesc/did/unitid',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Collection ID',
            'help_text': 'The unique identifier for the collection.	This ID will be created using the Densho ID Service.',
            'max_length':255,
            'widget':   '',
            'initial':  '',
            'required': True,
        },
        'default':    '',
    },
    {
        'name':       'origination',
        'xpath':      '/ead/archdesc/did/origination',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Creator',
            'help_text': 'The name of the person/people/organization responsible for the creation and/or assembly of the majority of materials in the collection. For individuals, "LastName, FirstName" (e.g. Adams, Ansel). Multiple creators are allowed but must be separated using a semi-colon.',
            'max_length':255,
            'widget':   '',
            'initial':  '',
            'required': False,
        },
        'default':    '',
    },
    {
        'name':       'physdesc',
        'xpath':      '/ead/archdesc/did/physdesc/extent',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Physical Description',
            'help_text': 'A statement about the extent of the collection.',
            'max_length':255,
            'widget':   '',
            'initial':  '',
            'required': False,
        },
        'default':    '',
    },
    {
        'name':       'langcode',
        'xpath':      '/ead/archdesc/did/langmaterial/language/@langcode',
        'model_type': str,
        'form_type':  forms.ChoiceField,
        'form': {
            'label':    'Language',
            'help_text': 'The language that predominates in the original material being described.	Only needed for objects containing textual content (i.e. caption on a photograph, text of a letter). Use the Library of Congress Codes for the Representation of Names of Languages ISO 639-2 Codes (found here http://www.loc.gov/standards/iso639-2/php/code_list.php).',
            'choices':  LANGUAGE_CHOICES,
            'widget':   '',
            'initial':  '',
            'required': False,
        },
        'default':    '',
    },
    {
        'name':       'repository',
        'xpath':      '/ead/archdesc/did/repository',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Contributing Institution',
            'help_text': 'The name of the organization that owns the physical materials.  In many cases this will be the partner\'s name unless the materials were borrowed from a different organization for scanning.',
            'max_length':255,
            'widget':   '',
            'initial':  '',
            'required': True,
        },
        'default':    '',
    },
    {
        'name':       'abstract',
        'xpath':      '/ead/archdesc/did/abstract',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Abstract',
            'help_text': 'A brief statement about the creator and the scope of the collection. Brief free text following basic Chicago Manual style guidelines.',
            'widget':   forms.Textarea,
            'initial':  '',
            'required': True,
        },
        'default':    '',
    },
    {
        'name':       'notes',
        'xpath':      '/ead/archdesc/did/note',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Notes',
            'help_text': 'Additional information about the collection that is not appropriate for any other element.',
            'widget':   forms.Textarea,
            'initial':  '',
            'required': False,
        },
        'default':    '',
    },
    {
        'name':       'physloc',
        'xpath':      '/ead/archdesc/did/physloc',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Physical Location',
            'help_text': 'The place where the collection is stored.	Could be the name of a building, shelf location, etc.',
            'widget':   forms.Textarea,
            'initial':  '',
            'required': False,
        },
        'default':    '',
    },
]

class CollectionOverviewForm(XMLForm):
    def __init__(self, *args, **kwargs):
        super(CollectionOverviewForm, self).__init__(*args, **kwargs)



ADMIN_INFO_FIELDS = [
    {
        'name':       'acqinfo',
        'xpath':      '/ead/descgrp/acqinfo',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Acquisition Information',
            'help_text': 'Information about how the collection was acquired.',
            'widget':   forms.Textarea,
            'initial':  '',
            'required': True,
        },
        'default':    '',
    },
    {
        'name':       'custodhist',
        'xpath':      '/ead/descgrp/custodhist',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Custodial History',
            'help_text': 'Information about the provenance of the collection.',
            'widget':   forms.Textarea,
            'initial':  '',
            'required': False,
        },
        'default':    '',
    },
    {
        'name':       'accruals',
        'xpath':      '/ead/descgrp/accruals',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Accruals',
            'help_text': 'Can be used to note if there were multiple donations made at different times or if additional materials are expected in the future.',
            'widget':   forms.Textarea,
            'initial':  '',
            'required': False,
        },
        'default':    '',
    },
    {
        'name':       'processinfo',
        'xpath':      '/ead/descgrp/processinfo',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Processing Information',
            'help_text': 'Information about accessioning, arranging, describing, preserving, storing, or otherwise preparing the described materials for research use. Free text field. Can include information about who processed the collection, who created/if there is a finding aid, deaccessioning, etc.',
            'widget':   forms.Textarea,
            'initial':  '',
            'required': False,
        },
        'default':    '',
    },
    {
        'name':       'accessrestrict',
        'xpath':      '/ead/descgrp/accessrestrict',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Restrictions on Access',
            'help_text': 'Information about any restrictions on access to the original physical materials.',
            'widget':   forms.Textarea,
            'initial':  '',
            'required': False,
        },
        'default':    '',
    },
    {
        'name':       'userrestrict',
        'xpath':      '/ead/descgrp/userrestrict',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Restrictions on Use',
            'help_text': 'Short statement about usage limitations and intellectual property for the individual object.',
            'widget':   forms.Textarea,
            'initial':  '',
            'required': False,
        },
        'default':    '',
    },
    {
        'name':       'prefercite',
        'xpath':      '/ead/descgrp/prefercite',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Preferred Citation',
            'help_text': 'Short courtesy text relating to the use of the object. Could identify either the collection contributor and/or donor depending on the deed of gift or usage agreement. Always begins with "Courtesy of . . ."',
            'widget':   forms.Textarea,
            'initial':  '',
            'required': True,
        },
        'default':    '',
    },
]

class AdminInfoForm(XMLForm):
    def __init__(self, *args, **kwargs):
        super(AdminInfoForm, self).__init__(*args, **kwargs)



BIOG_HIST_FIELDS = [
    {
        'name':       'bioghist',
        'xpath':      '/ead/bioghist',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Biography and History',
            'help_text': 'Provides contextual information about the collection. Often includes information about the creator(s) and/or time period.',
            'widget':   forms.Textarea,
            'initial':  '',
            'required': False,
        },
        'default':    '',
    },
]

class BiogHistForm(XMLForm):
    def __init__(self, *args, **kwargs):
        super(BiogHistForm, self).__init__(*args, **kwargs)



SCOPE_CONTENT_FIELDS = [
    {
        'name':       'scopecontent',
        'xpath':      '/ead/scopecontent',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Scope and Content',
            'help_text': 'Summarizes the characteristics of the materials, the functions and activities that produced them, and the types of information contained in them.',
            'widget':   forms.Textarea,
            'initial':  '',
            'required': False,
        },
        'default':    '',
    },
]

class ScopeContentForm(XMLForm):
    def __init__(self, *args, **kwargs):
        super(ScopeContentForm, self).__init__(*args, **kwargs)



ADJUNCT_DESCRIPTIVE_FIELDS = [
    {
        'name':       'relatedmaterial',
        'xpath':      '/ead/descgrp/relatedmaterial',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Related Materials',
            'help_text': 'Information about materials in other collections that might be of interest to researchers. Free text field. The addition of links will be available in the future.',
            'widget':   forms.Textarea,
            'initial':  '',
            'required': False,
        },
        'default':    '',
    },
    {
        'name':       'separatedmaterial',
        'xpath':      '/ead/descgrp/separatedmaterial',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Separated Materials',
            'help_text': 'Information about materials that were pulled from this collection and added to another. Free text field. The addition of links will be available in the future.',
            'widget':   forms.Textarea,
            'initial':  '',
            'required': False,
        },
        'default':    '',
    },
]

class AdjunctDescriptiveForm(XMLForm):
    def __init__(self, *args, **kwargs):
        super(AdjunctDescriptiveForm, self).__init__(*args, **kwargs)
