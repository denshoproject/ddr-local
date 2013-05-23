import datetime
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


EAD_XML = """<ead>
  <eadheader audience="internal" countryencoding="iso3166-1" dateencoding="iso8601" langencoding="iso639-2b" relatedencoding="DC" repositoryencoding="iso15511" scriptencoding="iso15924">
    <eadid countrycode="" identifier="" mainagencycode=""></eadid>
    <filedesc>
      <titlestmt>
        <titleproper encodinganalog="Title"></titleproper>
        <subtitle></subtitle>
        <author encodinganalog="Creator"></author>
      </titlestmt>
      <publicationstmt>
        <publisher encodinganalog="Publisher"></publisher>
        <date encodinganalog="Date" normal=""></date>
      </publicationstmt>
    </filedesc>
    <profiledesc>
      <creation>
        <date normal=""></date>
      </creation>
      <langusage>
        <language encodinganalog="Language" langcode=""></language>
      </langusage>
    </profiledesc>
  </eadheader>
  <archdesc level="collection" type="inventory" relatedencoding="MARC21">
    <did>
      <head></head>
      <repository encodinganalog="852$a" label="Repository: "></repository>
      <origination label="Creator: ">
         <persname encodinganalog="100"></persname>
      </origination>
      <unittitle encodinganalog="245$a" label="Title: "></unittitle>
      <unitdate encodinganalog="245$f" normal="" type="inclusive" label="Inclusive Dates: "></unitdate>
      <physdesc encodinganalog="300$a" label="Quantity: ">
         <extent></extent>
      </physdesc>
      <abstract encodinganalog="520$a" label="Abstract: "></abstract>
      <unitid encodinganalog="099" label="Identification: " countrycode="" repositorycode=""></unitid>
      <langmaterial label="Language: " encodinganalog="546">
         <language langcode=""></language>
      </langmaterial>
    </did>
  </archdesc>
  <dsc/>
</ead>"""

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
            'help_text': '',
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
            'label':    'Repository',
            'help_text': '',
            'max_length':255,
            'widget':   '',
            'initial':  '',
            'required': True,
        },
        'default':    'Repository Name Goes Here',
    },
    {
        'name':       'persname',
        'xpath':      '/ead/archdesc/did/origination/persname',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Origination Person Name',
            'help_text': '',
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
            'label':    'Unit Title',
            'help_text': '',
            'max_length':255,
            'widget':   '',
            'initial':  '',
            'required': True,
        },
        'default':    'John A. Doe Papers',
    },
    {
        'name':       'unitdate',
        'xpath':      '/ead/archdesc/did/unitdate',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Unit Date',
            'help_text': 'Start and end years (YYYY-YYYY).',
            'max_length':9,
            'widget':   '',
            'initial':  '',
            'required': True,
        },
        'default':    '1940-1950',
    },
    {
        'name':       'quantity',
        'xpath':      '/ead/archdesc/did/physdesc/extent',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':    'Quantity',
            'help_text': '',
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
            'help_text': '',
            'widget':   forms.Textarea,
            'initial':  '',
            'required': True,
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
            'help_text': '',
            'choices':  LANGUAGE_CHOICES,
            'widget':   '',
            'initial':  '',
            'required': True,
        },
        'default':    'eng',
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

class ArchDescForm(XMLForm):
    def __init__(self, *args, **kwargs):
        super(ArchDescForm, self).__init__(*args, **kwargs)
