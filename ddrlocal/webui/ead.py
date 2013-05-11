from copy import deepcopy
import StringIO

from lxml import etree

from django import forms
from django.utils.datastructures import SortedDict


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
</ead>"""

EADHEADER_FIELDS = [
    {
        'name': 'eadid',
        'type': forms.CharField,
        'xpath':     '/ead/eadheader/eadid',
        'label':     'eadid',
        'help_text': '',
        'widget':    '',
        'default':   '',
        'initial':   '',
        'max_length': 255,
        'required': True,
    },
#    {
#        'name': 'eadid_countrycode',
#        'type': forms.ChoiceField,
#        'xpath':     '/ead/eadheader/eadid@countrycode',
#        'label':     'Country',
#        'help_text': '',
#        'widget':    '',
#        'choices': COUNTRY_CHOICES,
#        'default':   '',
#        'initial':   '',
#        'required': True,
#    },
#    {
#        'name': 'eadid_identifier',
#        'type': forms.CharField,
#        'xpath':     '/ead/eadheader/eadid@identifier',
#        'label':     'eadid identifier',
#        'help_text': '',
#        'widget':    '',
#        'default':   '',
#        'initial':   '',
#        'max_length': 255,
#        'required': True,
#    },
#    {
#        'name': 'eadid_mainagencycode',
#        'type': forms.CharField,
#        'xpath':     '/ead/eadheader/eadid@mainagencycode',
#        'label':     'agency code',
#        'help_text': '',
#        'widget':    '',
#        'default':   '',
#        'initial':   '',
#        'max_length': 255,
#        'required': True,
#    },
    {
        'name': 'titlestmt_titleproper',
        'type': forms.CharField,
        'xpath':     '/ead/eadheader/filedesc/titlestmt/titleproper',
        'label':     'Title',
        'help_text': '',
        'widget':    '',
        'default':   '',
        'initial':   '',
        'max_length': 255,
        'required': True,
    },
    {
        'name': 'titlestmt_subtitle',
        'type': forms.CharField,
        'xpath':     '/ead/eadheader/filedesc/titlestmt/subtitle',
        'label':     'Subtitle',
        'help_text': '',
        'widget':    '',
        'default':   '',
        'initial':   '',
        'max_length': 255,
        'required': False,
    },
    {
        'name': 'titlestmt_author',
        'type': forms.CharField,
        'xpath':     '/ead/eadheader/filedesc/titlestmt/author',
        'label':     'Creator',
        'help_text': '',
        'widget':    '',
        'default':   '',
        'initial':   '',
        'max_length': 255,
        'required': True,
    },
    {
        'name': 'publicationstmt_publisher',
        'type': forms.CharField,
        'xpath':     '/ead/eadheader/filedesc/publicationstmt/publisher',
        'label':     'Publisher',
        'help_text': '',
        'widget':    '',
        'default':   '',
        'initial':   '',
        'max_length': 255,
        'required': True,
    },
    {
        'name': 'publicationstmt_date',
        'type': forms.CharField,
        'xpath':     '/ead/eadheader/filedesc/publicationstmt/date',
        'label':     'Publication Date',
        'help_text': '',
        'widget':    '',
        'default':   '',
        'initial':   '',
        'max_length': 255,
        'required': True,
    },
    {
        'name': 'profiledesc_creation',
        'type': forms.CharField,
        'xpath':     '/ead/eadheader/profiledesc/creation',
        'label':     'Profile Creator',
        'help_text': '',
        'widget':    '',
        'default':   '',
        'initial':   '',
        'max_length': 255,
        'required': True,
    },
#    {
#        'name': 'profiledesc_date',
#        'type': forms.DateField,
#        'xpath':     '/ead/eadheader/profiledesc/date',
#        'label':     'Profile Date',
#        'help_text': '',
#        'widget':    '',
#        'default':   '',
#        'initial':   '',
#        'required': True,
#    },
#    {
#        'name':      'langcode',
#        'type':      forms.ChoiceField,
#        'xpath':     '/ead/eadheader/profiledesc/langusage/language@langcode',
#        'label':     'Language',
#        'help_text': '',
#        'widget':    '',
#        'choices':   LANGUAGE_CHOICES,
#        'default':   '',
#        'initial':   '',
#        'required':  True,
#    },
]

ARCHDESC_FIELDS = [
    {
        'name':      'head',
        'type':      forms.CharField,
        'xpath':     '/ead/archdesc/did/head',
        'label':     'Head',
        'help_text': '',
        'widget':    '',
        'default':   'Collection Overview',
        'initial':   '',
        'required':  True,
    },
    {
        'name':     'repository',
        'type':     forms.CharField,
        'xpath':    '/ead/archdesc/did/repository',
        'label':    'Repository',
        'help_text': '',
        'max_length':255,
        'widget':   '',
        'default':  'Repository Name Goes Here',
        'initial':  '',
        'required': True
    },
    {
        'name':     'persname',
        'type':     forms.CharField,
        'xpath':    '/ead/archdesc/did/origination/persname',
        'label':    'Origination Person Name',
        'help_text': '',
        'max_length':255,
        'widget':   '',
        'default':  'Doe, John A. (John Doe), 1911-1992',
        'initial':  '',
        'required': True
    },
    {
        'name':     'unittitle',
        'type':     forms.CharField,
        'xpath':    '/ead/archdesc/did/unittitle',
        'label':    'Unit Title',
        'help_text': '',
        'max_length':255,
        'widget':   '',
        'default':  'John A. Doe Papers',
        'initial':  '',
        'required': True
    },
    {
        'name':     'unitdate',
        'type':     forms.CharField,
        'xpath':    '/ead/archdesc/did/unitdate',
        'label':    'Unit Date',
        'help_text': 'Start and end years (YYYY-YYYY).',
        'max_length':9,
        'widget':   '',
        'default':  '1940-1950',
        'initial':  '',
        'required': True
    },
    {
        'name':     'quantity',
        'type':     forms.CharField,
        'xpath':    '/ead/archdesc/did/physdesc/extent',
        'label':    'Quantity',
        'help_text': '',
        'max_length':255,
        'widget':   '',
        'default':  'N linear ft.',
        'initial':  '',
        'required': True
    },
    {
        'name':     'abstract',
        'type':     forms.CharField,
        'xpath':    '/ead/archdesc/did/abstract',
        'label':    'Abstract',
        'help_text': '',
        'widget':   forms.Textarea,
        'default':  '',
        'initial':  '',
        'required': True
    },
    {
        'name':     'langcode',
        'type':     forms.ChoiceField,
        'xpath':    '/ead/archdesc/did/langmaterial/language/@langcode',
        'label':    'Language',
        'help_text': '',
        'choices':  LANGUAGE_CHOICES,
        'widget':   '',
        'default':  'eng',
        'initial':  '',
        'required': True
    },
]


class XMLForm(forms.Form):
    
    def __init__(self, *args, **kwargs):
        """Adds specified form fields
        
        Form fields must be provided in kwargs['fields']
        Examples:
            form = XMLForm(fields=fields)
            form = XMLForm(request.POST, fields=fields)
        
        fields must be in the following format:
            fields = [
                {
                    'name':     'abstract',
                    'type':     forms.CharField,
                    'xpath':    '/ead/archdesc/did/abstract',
                    'label':    'Abstract',
                    'help_text': '',
                    'widget':   forms.Textarea,
                    'default':  '',
                    'initial':  '',
                    'required': True
                },
                ...
            ]
        
        Notes:
        - type and widget are Django forms field objects, not strings.
        - label, help_text, widget, initial, and required are the required
          Django field args and will be passed in directly to the Form object.
        """
        if kwargs.has_key('fields'):
            field_kwargs = kwargs.pop('fields')
        else:
            field_kwargs = []
        super(XMLForm, self).__init__(*args, **kwargs)
        fields = []
        for fkwargs in deepcopy(field_kwargs): # don't modify kwargs here
            # remove fields that Django doesn't accept
            fargs = []
            fname = fkwargs.pop('name')
            ftype = fkwargs.pop('type')
            xpath = fkwargs.pop('xpath')
            if 'default' in fkwargs:
                fkwargs.pop('default')
            # instantiate Field object and to list
            fobject = ftype(*fargs, **fkwargs)
            fields.append((fname, fobject))
        # Django Form object takes a SortedDict rather than list
        self.fields = SortedDict(fields)

    @staticmethod
    def prep_fields(fields, xml):
        """Takes raw kwargs, fills in initial data from xml file.
        
        kwargs[*]['initial'] is used to populate form fields
        """
        thistree = etree.parse(StringIO.StringIO(xml))
        for f in fields:
            if f.get('default',None):
                f.pop('default') # Django forms won't accept this
            # default value from xml, if any
            initial = None
            tag = None
            tags = thistree.xpath(f['xpath'])
            if tags and len(tags):
                if (type(tags) == type([])):
                    tag = tags[0]
                else:
                    tag = tags
            if hasattr(tag, 'text'):
                initial = tag.text
            elif type(tag) == type(''):
                initial = tag
            if initial:
                f['initial'] = initial.strip()
        return fields
    
    @staticmethod
    def process(xml, fields, form):
        """Writes form.cleaned_data values to XML
        
        Uses XPaths from field_kwargs
        """
        tree = etree.parse(StringIO.StringIO(xml))
        for f in deepcopy(fields):
            name = f['name']
            xpath = f['xpath']
            cleaned_data = form.cleaned_data[name]
            tags = tree.xpath(xpath)
            if tags and len(tags):
                if (type(tags) == type([])):
                    tag = tags[0]
                else:
                    tag = tags
            if hasattr(tag, 'text'):
                tag.text = cleaned_data
            elif type(tag) == type(''):
                tag = cleaned_data
        return etree.tostring(tree, pretty_print=True)
