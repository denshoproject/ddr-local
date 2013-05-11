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
