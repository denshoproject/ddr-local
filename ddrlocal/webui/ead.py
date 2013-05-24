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
