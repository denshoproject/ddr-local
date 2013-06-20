from datetime import datetime, date
import json
import os

from bs4 import BeautifulSoup

from django import forms
from django.conf import settings

import tematres


DATE_FORMAT = '%Y-%m-%d'
DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'
# Django uses a slightly different datetime format
DATETIME_FORMAT_FORM = '%Y-%m-%d %H:%M:%S'



LANGUAGE_CHOICES = [['eng','English'],
                    ['jpn','Japanese'],
                    ['esp','Spanish'],]



class Entity(object):
    id = ''
    path = None

    def repo(self):
        return self.id.split('-')[0]
    
    def org(self):
        return self.id.split('-')[1]
    
    def cid(self):
        return self.id.split('-')[2]
    
    def eid(self):
        return self.id.split('-')[3]
    
    def collection_uid(self):
        return self.id.rsplit('-',1)[0]
    
    @staticmethod
    def json_path(repo, org, cid, eid):
        collection_uid = '{}-{}-{}'.format(repo, org, cid)
        entity_uid     = '{}-{}-{}-{}'.format(repo, org, cid, eid)
        collection_abs = os.path.join(settings.DDR_BASE_PATH, collection_uid)
        entity_abs     = os.path.join(collection_abs,'files',entity_uid)
        path = os.path.join(entity_abs, 'entity.json')
        return path
    
    def changelog_path(self, rel=False):
        path_rel = 'changelog'
        if rel:
            return path_rel
        return os.path.join(self.path, path_rel)
    
    def mets_xml_path(self, rel=False):
        path_rel = 'mets.xml'
        if rel:
            return path_rel
        return os.path.join(self.path, path_rel)
    
    def parent_path(self):
        return os.path.split(os.path.split(self.path)[0])[0]
        
    def files_path(self, rel=False):
        path_rel = 'files'
        if rel:
            return path_rel
        return os.path.join(self.path, path_rel)
    
    def changelog(self):
        return open(self.changelog_path(), 'r').read()
    
    def json(self):
        path = Entity.json_path(self.repo(), self.org(), self.cid(), self.eid())
        return open(path, 'r').read()
    
    def mets_xml(self):
        return open(self.mets_xml_path(), 'r').read()
    
    def files(self):
        """Given a BeautifulSoup-ified METS doc, get list of entity files
        
        ...
        <fileSec>
         <fileGrp USE="master">
          <file CHECKSUM="fadfbcd8ceb71b9cfc765b9710db8c2c" CHECKSUMTYPE="md5">
           <Flocat href="files/6a00e55055.png"/>
          </file>
         </fileGrp>
         <fileGrp USE="master">
          <file CHECKSUM="42d55eb5ac104c86655b3382213deef1" CHECKSUMTYPE="md5">
           <Flocat href="files/20121205.jpg"/>
          </file>
         </fileGrp>
        </fileSec>
        ...
        """
        self_dict = self.__dict__
        assert False
        soup = BeautifulSoup(self.mets_xml(), 'xml')
        files = []
        for tag in soup.find_all('flocat', 'xml'):
            f = {
                'abs': os.path.join(self.path, tag['href']),
                'name': os.path.join(self.path, tag['href']),
                'basename': os.path.basename(tag['href']),
                'size': 1234567,
            }
            files.append(f)
        return files
    
    def labels_values(self):
        """Generic display
        """
        lv = []
        for mf in METS_FIELDS:
            if hasattr(self, mf['name']) and mf.get('form',None):
                item = {'label': mf['form']['label'],
                        'value': getattr(self, mf['name'])}
                lv.append(item)
        return lv

    def form_data(self):
        """Prep data dict to pass into EntityForm object.
        
        Certain fields may require special processing, which will be performed
        by the function specified in field['prep_func'].
        
        @returns data: dict object as used by Django Form object.
        """
        data = {}
        for mf in METS_FIELDS:
            if hasattr(self, mf['name']) and mf.get('form',None):
                key = mf['name']
                value = getattr(self, mf['name'])
                # hand off special processing to function specified in METS_FIELDS
                if mf.get('prep_func',None):
                    func = mf['prep_func']
                    value = func(value)
                # end special processing
                data[key] = value
        return data

    def form_process(self, form):
        """Process cleaned_data coming from EntityForm
        
        Certain fields may require special processing, which will be performed
        by the function specified in field['proc_func'].
        
        @param form
        """
        for mf in METS_FIELDS:
            if hasattr(self, mf['name']) and mf.get('form',None):
                key = mf['name']
                cleaned_data = form.cleaned_data[key]
                # hand off special processing to function specified in METS_FIELDS
                if mf.get('proc_func',None):
                    func = mf['proc_func']
                    cleaned_data = func(cleaned_data)
                # end special processing
                setattr(self, key, cleaned_data)
    
    @staticmethod
    def load(path):
        if '.json' in path:
            return Entity._load_json(path)
        elif '.xml' in path:
            return Entity._load_xml(path)
        return None
    
    def dump(self, path):
        if '.json' in path:
            return self._dump_json(path)
        elif '.xml' in path:
            return self._dump_xml(path)
        return None
    
    @staticmethod
    def _load_json(path):
        """Load Entity from .json file.
        @param path: Absolute path to .json file.
        """
        with open(path, 'r') as f:
            e = json.loads(f.read())
        if e:
            entity = Entity()
            entity.path = os.path.dirname(path)
            for mf in METS_FIELDS:
                for f in e:
                    if f.keys()[0] == mf['name']:
                        setattr(entity, f.keys()[0], f.values()[0])
            # special cases
            if not entity.id:
                entity.id = os.path.split(os.path.dirname(path))[1]
            if entity.created:
                entity.created = datetime.strptime(entity.created, DATETIME_FORMAT)
            else:
                entity.created = datetime.now()
            if entity.lastmod:
                entity.lastmod = datetime.strptime(entity.lastmod, DATETIME_FORMAT)
            else:
                entity.lastmod = datetime.now()
            if entity.digitize_date:
                entity.digitize_date = datetime.strptime(entity.digitize_date, DATE_FORMAT)
            else:
                entity.digitize_date = ''
            # end special cases
            return entity
        return None
    
    def _dump_json(self, path):
        """Dump Entity data to .json file.
        @param path: Absolute path to .json file.
        """
        entity = []
        for mf in METS_FIELDS:
            if hasattr(self, mf['name']):
                item = {}
                key = mf['name']
                val = getattr(self, mf['name'])
                # special cases
                if key in ['created', 'lastmod']:
                    val = val.strftime(DATETIME_FORMAT)
                elif key in ['digitize_date']:
                    val = val.strftime(DATE_FORMAT)
                # end special cases
                item[key] = val
                entity.append(item)
        json_pretty = json.dumps(entity, indent=4, separators=(',', ': '))
        with open(path, 'w') as f:
            f.write(json_pretty)
    
    @staticmethod
    def _load_xml(path):
        """Load Entity from .xml file.
        @param path: Absolute path to .xml file.
        """
        return None
    
    def _dump_xml(self, path):
        """Dump Entity to .xml file.
        @param path: Absolute path to .xml file.
        """
        pass

    @staticmethod
    def create(path):
        """Creates a new entity with the specified entity ID.
        @param path: Absolute path; must end in valid DDR entity id.
        """
        entity = Entity()
        for mf in METS_FIELDS:
            if hasattr(mf, 'name') and hasattr(mf, 'initial'):
                setattr(entity, mf['name'], mf['initial'])
        entity.id = eid
        entity.path = path
        return entity




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

def prepare_persons(data):    return _prepare_basic(data)
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

def process_persons(data):    return _process_basic(data)
def process_facility(data):   return _process_basic(data)
# notes


# ----------------------------------------------------------------------

METS_FIELDS = [
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
        'default':    '',
    },
    {
        'name':       'created',
        'xpath':      "",
        'xpath_dup':  [],
        'model_type': datetime,
        'form_type':  forms.DateTimeField,
        'form': {
            'label':      '',
            'help_text':  '',
            'widget':     forms.HiddenInput,
            'initial':    '',
            'required':   True,
        },
        'default':    '',
    },
    {
        'name':       'lastmod',
        'xpath':      "",
        'xpath_dup':  [],
        'model_type': datetime,
        'form_type':  forms.DateTimeField,
        'form': {
            'label':      '',
            'help_text':  '',
            'widget':     forms.HiddenInput,
            'initial':    '',
            'required':   True,
        },
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
        'default':    '',
    },
    {
        'name':       'genre',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:genre",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Object Genre',
            'help_text':  'The genre, form, and/or physical characteristics of the object.	Use the Library of Congress Basic Genre Terms for Cultural Heritage Materials controlled vocabulary list. See Appendix E: Controlled Vocabularies or the Library of Congress website: http://memory.loc.gov/ammem/techdocs/genre.html',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    {
        'name':       'format',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:typeOfResource",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Object Format',
            'help_text':  'A descriptor for indicating the type of object.	Use the Densho Object Type Controlled Vocabulary List found in Appendix E: Controlled Vocabularies.',
            'max_length': 255,
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
        'form_type':  forms.CharField,
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
        'form_type':  forms.CharField,
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
            'help_text':  'Short courtesy text relating to use of object.	Could identify either collection contributor and/or donor depending on deed of gift and/or usage agreement for object. Always begins with: "Courtesy of"',
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
        'default':    '',
    },
    {
        'name':       'persons',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:subject/mods:name/mods:namePart",
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
