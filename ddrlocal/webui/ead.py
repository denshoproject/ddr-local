import StringIO

from bs4 import BeautifulSoup
from lxml import etree

from django import forms


COUNTRY_CHOICES = [['us','US'],
                   ['ca','Canada'],
                   ['jp','Japan'],]

LANGUAGE_CHOICES = [['en','English'],
                    ['ja','Japanese'],
                    ['es','Spanish'],]

def repository_codes():
    return [('ddr-densho','ddr-densho'),
            ('ddr-testing','ddr-testing'),]

eadheaderxml = """<eadheader audience="internal" countryencoding="iso3166-1" 
dateencoding="iso8601" langencoding="iso639-2b" 
relatedencoding="DC" repositoryencoding="iso15511" 
scriptencoding="iso15924">
   <eadid countrycode="us" identifier="bachrach_lf" mainagencycode="NSyU">bachrach_lf</eadid>
   <filedesc>
      <titlestmt>
         <titleproper encodinganalog="Title">Louis Fabian Bachrach Papers</titleproper>
         <subtitle>An inventory of his papers at Blank University</subtitle>
         <author encodinganalog="Creator">Mary Smith</author>
      </titlestmt>
      <publicationstmt>
         <publisher encodinganalog="Publisher">Blank University</publisher>
         <date encodinganalog="Date" normal="1981">1981</date>
      </publicationstmt>
   </filedesc>
   <profiledesc>
      <creation>John Jones
         <date normal="2006-09-13">13 Sep 2006</date>
      </creation>
      <langusage>
         <language encodinganalog="Language" langcode="eng">English</language>
      </langusage>
   </profiledesc>
</eadheader>"""

class EADHeaderForm(forms.Form):
    audience              = forms.CharField(max_length=255, required=True, initial='internal',)
    countryencoding       = forms.CharField(max_length=255, required=True, initial='iso3166-1',)
    dateencoding          = forms.CharField(max_length=255, required=True, initial='iso8601',)
    langencoding          = forms.CharField(max_length=255, required=True, initial='iso639-2b',) 
    relatedencoding       = forms.CharField(max_length=255, required=True, initial='DC',)
    repositoryencoding    = forms.CharField(max_length=255, required=True, initial='iso15511',)
    scriptencoding        = forms.CharField(max_length=255, required=True, initial='iso15924',)
    
    eadid                 = forms.CharField(max_length=255, required=True,)
    eadid_countrycode     = forms.ChoiceField(required=True, choices=COUNTRY_CHOICES,)
    eadid_identifier      = forms.CharField(max_length=255, required=True,)
    eadid_mainagencycode  = forms.CharField(max_length=255, required=True,)
    
    titlestmt_titleproper = forms.CharField(max_length=255, required=True,)
    titlestmt_subtitle    = forms.CharField(max_length=255, required=True,)
    titlestmt_author      = forms.CharField(max_length=255, required=True,)
    
    publicationstmt_publisher = forms.CharField(max_length=255, required=True,)
    publicationstmt_date  = forms.CharField(max_length=255, required=True,)
    
    profiledesc_creation  = forms.CharField(max_length=255, required=True,)
    profiledesc_date      = forms.DateField(required=True,)
    
    langcode              = forms.ChoiceField(required=True, choices=LANGUAGE_CHOICES,)


def prep_eadheader_form(xml):
    """Load data from existing EAD.xml into form.
    """
    data = {}
    soup = BeautifulSoup(xml, 'xml')
    soup = eadheader_expand(soup)
    
    data['audience']           = soup.ead.eadheader.get('audience', 'internal')
    data['countryencoding']    = soup.ead.eadheader.get('countryencoding', 'iso3166-1')
    data['dateencoding']       = soup.ead.eadheader.get('dateencoding', 'iso8601')
    data['langencoding']       = soup.ead.eadheader.get('langencoding', 'iso639-2b')
    data['relatedencoding']    = soup.ead.eadheader.get('relatedencoding', 'DC')
    data['repositoryencoding'] = soup.ead.eadheader.get('repositoryencoding', 'iso15511')
    data['scriptencoding']     = soup.ead.eadheader.get('scriptencoding', 'iso15924')

    data['eadid_countrycode']    = soup.ead.eadid.get('eadid_countrycode', 'us')
    data['eadid_identifier']     = soup.ead.eadid.get('eadid_identifier', None)
    data['eadid_mainagencycode'] = soup.ead.eadid.get('eadid_mainagencycode', None)
    data['eadid']                = soup.ead.eadid.string
    
    data['titlestmt_titleproper'] = soup.ead.eadheader.filedesc.titlestmt.titleproper.text
    data['titlestmt_subtitle']    = soup.ead.eadheader.filedesc.titlestmt.subtitle.text
    data['titlestmt_author']      = soup.ead.eadheader.filedesc.titlestmt.author.text
    
    data['publicationstmt_publisher'] = soup.ead.eadheader.filedesc.publicationstmt.publisher.string
    data['publicationstmt_date']      = soup.ead.eadheader.filedesc.publicationstmt.date.string
    
    data['profiledesc_creation'] = soup.ead.eadheader.profiledesc.creation.string
    data['profiledesc_date']     = soup.ead.eadheader.profiledesc.creation.date.get('normal', '')
     
    data['langcode'] = soup.ead.eadheader.profiledesc.langusage.language.get('langcode', '')

    for key,val in data.iteritems():
        if val:
            data[key] = val.strip()
    
    form = EADHeaderForm(data)
    return form

def eadheader_expand(soup):
    """Add tags if they're not already present.
    """
    if not soup.ead.eadheader:             soup.ead.append(soup.new_tag('eadheader'))
    if not soup.ead.eadheader.eadid:       soup.ead.eadheader.append(soup.new_tag('eadid'))
    if not soup.ead.eadheader.filedesc:    soup.ead.eadheader.append(soup.new_tag('filedesc'))
    if not soup.ead.eadheader.profiledesc: soup.ead.eadheader.append(soup.new_tag('profiledesc'))
    
    if not soup.ead.eadheader.filedesc.titlestmt:
        soup.ead.eadheader.filedesc.append(soup.new_tag('titlestmt'))
    if not soup.ead.eadheader.filedesc.titlestmt.titleproper:
        soup.ead.eadheader.filedesc.titlestmt.append(soup.new_tag('titleproper'))
    if not soup.ead.eadheader.filedesc.titlestmt.subtitle:
        soup.ead.eadheader.filedesc.titlestmt.append(soup.new_tag('subtitle'))
    if not soup.ead.eadheader.filedesc.titlestmt.author:
        soup.ead.eadheader.filedesc.titlestmt.append(soup.new_tag('author'))
    
    if not soup.ead.eadheader.filedesc.publicationstmt:
        soup.ead.eadheader.filedesc.append(soup.new_tag('publicationstmt'))
    if not soup.ead.eadheader.filedesc.publicationstmt.publisher:
        soup.ead.eadheader.filedesc.publicationstmt.append(soup.new_tag('publisher'))
    if not soup.ead.eadheader.filedesc.publicationstmt.date:
        soup.ead.eadheader.filedesc.publicationstmt.append(soup.new_tag('date'))
    
    if not soup.ead.eadheader.profiledesc.creation:
        soup.ead.eadheader.profiledesc.append(soup.new_tag('creation'))
    if not soup.ead.eadheader.profiledesc.creation.date:
        soup.ead.eadheader.profiledesc.creation.append(soup.new_tag('date'))
    if not soup.ead.eadheader.profiledesc.langusage:
        soup.ead.eadheader.profiledesc.append(soup.new_tag('langusage'))
    if not soup.ead.eadheader.profiledesc.langusage.langusage:
        soup.ead.eadheader.profiledesc.langusage.append(soup.new_tag('language'))
    
    return soup

def eadheader_xml(form, xml):
    """
    """
    soup = BeautifulSoup(xml, 'xml')
    soup = eadheader_expand(soup)
        
    soup.ead.eadheader['audience']           = form.cleaned_data.get('audience',           'internal')
    soup.ead.eadheader['countryencoding']    = form.cleaned_data.get('countryencoding',    'iso3166-1')
    soup.ead.eadheader['dateencoding']       = form.cleaned_data.get('dateencoding',       'iso8601')
    soup.ead.eadheader['langencoding']       = form.cleaned_data.get('langencoding',       'iso639-2b')
    soup.ead.eadheader['relatedencoding']    = form.cleaned_data.get('relatedencoding',    'DC')
    soup.ead.eadheader['repositoryencoding'] = form.cleaned_data.get('repositoryencoding', 'iso15511')
    soup.ead.eadheader['scriptencoding']     = form.cleaned_data.get('scriptencoding',     'iso15924')
    
    soup.ead.eadheader.eadid['eadid_countrycode'] = form.cleaned_data.get('eadid_countrycode','us')
    soup.ead.eadheader.eadid['eadid_identifier'] = form.cleaned_data.get('eadid_identifier','')
    soup.ead.eadheader.eadid['eadid_mainagencycode'] = form.cleaned_data.get('eadid_mainagencycode','')
    soup.ead.eadheader.eadid.string = form.cleaned_data.get('eadid','')

    soup.ead.eadheader.filedesc.titlestmt.titleproper['encodinganalog'] = 'Title'
    soup.ead.eadheader.filedesc.titlestmt.titleproper.string = form.cleaned_data.get('titlestmt_titleproper','')
    soup.ead.eadheader.filedesc.titlestmt.subtitle.string = form.cleaned_data.get('titlestmt_subtitle','')
    soup.ead.eadheader.filedesc.titlestmt.author['encodinganalog'] = 'Creator'
    soup.ead.eadheader.filedesc.titlestmt.author.string = form.cleaned_data.get('titlestmt_author','')
    
    soup.ead.eadheader.filedesc.publicationstmt.publisher['encodinganalog'] = 'Publisher'
    soup.ead.eadheader.filedesc.publicationstmt.publisher.string = form.cleaned_data.get('publicationstmt_publisher','')
    #soup.ead.eadheader.filedesc.publicationstmt.date['encodinganalog'] = 'Date'
    #soup.ead.eadheader.filedesc.publicationstmt.date['normal'] = form.cleaned_data.get('publicationstmt_date','')
    #soup.ead.eadheader.filedesc.publicationstmt.date.string = form.cleaned_data.get('publicationstmt_date','')
    
    #soup.ead.eadheader.profiledesc.creation.date['normal'] = form.cleaned_data.get('profiledesc_date','')
    #soup.ead.eadheader.profiledesc.creation.date.string = form.cleaned_data.get('profiledesc_date','')
    soup.ead.eadheader.profiledesc.creation.string = form.cleaned_data.get('profiledesc_creation','')
    
    soup.ead.eadheader.profiledesc.langusage.language['encodinganalog'] = 'Language'
    soup.ead.eadheader.profiledesc.langusage.language['langcode'] = form.cleaned_data.get('langcode','')
    soup.ead.eadheader.profiledesc.langusage.language.string = form.cleaned_data.get('langcode','')
    
    xml_new = soup.prettify()
    return xml_new






"""

Have a master EAD.xml
generate forms by running set of fieldname:type:required:xpath tuples through a function
evaluate form using same list of tuples
Ideally, prep and evaluate would be functions and not have to know anything about the XML
Templates can be hand-coded

"""


ARCHDESC_XML = """
<ead>
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

def archdesc_fields(model_xml, set_initial=False):
    """Prepares a set of kwargs describing fields
    Takes data from model_xml to populate initial values.
    
    """
    kwargs = [
        {
            'name':      'head',
            'type':      forms.CharField,
            'xpath':     '/ead/archdesc/did/head',
            'label':     'Head',
            'help_text': '',
            'widget':    '',
            'initial':   'Overview of the Collection',
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
            'initial':  'Blank University',
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
            'initial':  'Brightman, Samuel C. (Samuel Charles), 1911-1992',
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
            'initial':  'Samuel C. Brightman Papers',
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
            'initial':  '1932-1992',
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
            'initial':  '6 linear ft.',
            'required': True
        },
        {
            'name':     'abstract',
            'type':     forms.CharField,
            'xpath':    '/ead/archdesc/did/abstract',
            'label':    'Abstract',
            'help_text': '',
            'widget':   forms.Textarea,
            'initial':  'Papers of the American journalist including some war correspondence, political and political humor writings, and adult education material',
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
            'initial':  '',
            'required': True
        },
    ]
    if set_initial:
        tree = etree.parse(StringIO.StringIO(model_xml))
        for f in kwargs:
            # default value from model_xml, if any
            initial = None
            default = None
            defaults = tree.xpath(f['xpath'])
            if defaults and len(defaults):
                if (type(defaults) == type([])):
                    default = defaults[0]
                else:
                    default = defaults
            if hasattr(default, 'text'):
                initial = default.text
            elif type(default) == type(''):
                initial = default
            if initial:
                f['initial'] = initial.strip()
    return kwargs




widgets = {'forms.Textarea': forms.Textarea,}

from django.utils.datastructures import SortedDict

class ArchdescForm(forms.Form):
    
    def __init__(self, *args, **kwargs):
        """Builds form from self.model_xml, self.json; populates from collection xml.
        
        very very loosely modeled on django.forms.models.fields_for_model

        if request.GET:
            kwargs = archdesc_fields(ARCHDESC_XML)
            form = ArchdescForm(field_kwargs=kwargs)
        if request.POST:
            new_xml = ArchdescForm.process(field_kwargs=kwargs, form)
        
        @param xml The collection's XML document
        """
        if kwargs.has_key('field_kwargs'):
            field_kwargs = kwargs.pop('field_kwargs')
        else:
            field_kwargs = []
        super(ArchdescForm, self).__init__(*args, **kwargs)
        fields = []
        for fkwargs in field_kwargs:
            fname = fkwargs.pop('name')
            ftype = fkwargs.pop('type')
            xpath = fkwargs.pop('xpath')
            ## default value from self.model_xml, if any
            #default = None
            #defaults = etree.parse(StringIO.StringIO(self.model_xml)).xpath(xpath)
            #lendefaults = len(defaults)
            #typedefaults = type(defaults)
            #if defaults and len(defaults):
            #    if (type(defaults) == type([])):
            #        default = defaults[0]
            #    else:
            #        default = defaults
            #if hasattr(default, 'text') and default.text:
            #    fkwargs['initial'] = default.text.strip()
            #elif type(default) == type(''):
            #    fkwargs['initial'] = default.strip()
            
            #dlen = len(d)
            #dtag = d[0].tag
            #dtext = d[0].text
            #d0 = d[0]
            #ltype = type([])
            #dtype = type(d)
            #d_is_list = (type(d) == type([]))
            #d0type = type(d[0])
            #d_dict = d0.__dict__
            
            ##    fkwargs['initial'] = self.model_xml(xpath)
            ### initial value from collection_xml overrides that from model_xml
            #c = etree.parse(StringIO.StringIO(collection_xml)).xpath(xpath)
            #assert False
            ##if collection_xml(xpath):
            ##    fkwargs['initial'] = collection_xml(xpath)
            fargs = []
            fobject = ftype(*fargs, **fkwargs)
            fields.append((fname, fobject))
        self.fields = SortedDict(fields)

    @staticmethod
    def prep_data(model_xml):
        """Reads in model_xml and
        """
        data = {}
        for f in archdesc_fields():
            # default value from self.model_xml, if any
            initial = None
            default = None
            defaults = etree.parse(StringIO.StringIO(model_xml)).xpath(f['xpath'])
            if defaults and len(defaults):
                if (type(defaults) == type([])):
                    default = defaults[0]
                else:
                    default = defaults
            if default and hasattr(default, 'text') and default.text:
                initial = default.text.strip()
            elif type(default) == type(''):
                initial = default.strip()
            if initial:
                data[f['name']] = initial
        return data
    
    @staticmethod
    def process(xml, field_kwargs, form):
        """Set values in the XML using data from form.cleaned_data and xpaths from field_kwargs
        """
        tree = etree.parse(StringIO.StringIO(xml))
        for f in field_kwargs:
            name = f['name']
            xpath = f['xpath']
            cleaned_data = form.cleaned_data[name]
            tag = tree.xpath(xpath)
            assert False
