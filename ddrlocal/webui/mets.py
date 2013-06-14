from datetime import datetime
import os
import StringIO

from lxml import etree

from django import forms


import xmlforms
from xmlforms.forms import XMLForm
import tematres


METS_XML = ''
xml_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'mets.xml')
with open(xml_path, 'r') as f:
    METS_XML = f.read()

NAMESPACES = {
    'mets':  'http://www.loc.gov/METS/',
    'mix':   'http://www.loc.gov/mix/v10',
    'mods':  'http://www.loc.gov/mods/v3',
    'rts':   'http://cosimo.stanford.edu/sdr/metsrights/',
    'xlink': 'http://www.w3.org/1999/xlink',
    'xsi':   'http://www.w3.org/2001/XMLSchema-instance',
}

NAMESPACES_TAGPREFIX = {}
for k,v in NAMESPACES.iteritems():
    NAMESPACES_TAGPREFIX[k] = '{%s}' % v

NAMESPACES_XPATH = {'mets': NAMESPACES['mets'],}

NSMAP = {None : NAMESPACES['mets'],}
NS = NAMESPACES_TAGPREFIX
ns = NAMESPACES_XPATH



LANGUAGE_CHOICES = [['eng','English'],
                    ['jpn','Japanese'],
                    ['esp','Spanish'],]




 


METS_FIELDS = [
    {
        'name':       'entity_id',
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
        'default':    '',
    },
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
        'name':       'created',
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
        'default':    '',
    },
#    {
#        'name':       'location',
#        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:originInfo/mods:place/mods:placeTerm[@type='text']",
#        'xpath_dup':  [],
#        'model_type': str,
#        'form_type':  forms.CharField,
#        'form': {
#            'label':      'Location',
#            'help_text':  'Geographic area of the subject (i.e., where a photograph was taken). Could be place of creation for a document.	City, State (state name spelled out). Include country if outside the US (i.e., City, State, Country).',
#            'max_length': 255,
#            'widget':     '',
#            'initial':    '',
#            'required':   False,
#        },
#        'default':    '',
#    },
    {
        'name':       'creator',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:name/mods:namePart",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Creator',
            'help_text':  'For photographs, the name of the photographer. For letters, documents and other written materials, the name of the author. For newspapers, magazine and other printed matter, the name of the publisher.	For individuals, "LastName, FirstName: CreatorRole" (e.g., "Adams, Ansel:photographer"). Multiple creators are allowed, but must be separated using a semi-colon.',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   False,
        },
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
##    {
##        'name':       'digitizing_person',
##        'xpath':      '',
##        'xpath_dup':  [],
##        'model_type': str,
##        'form_type':  forms.CharField,
##        'form': {
##            'label':      'Digitizer',
##            'help_text':  'Name of person who created the scan. LastName, FirstName',
##            'max_length': 255,
##            'widget':     '',
##            'initial':    '',
##            'required':   True,
##        },
##        'default':    '',
##    },
##    {
##        'name':       'digitizing_organization_id',
##        'xpath':      '',
##        'xpath_dup':  [],
##        'model_type': str,
##        'form_type':  forms.CharField,
##        'form': {
##            'label':      'Digitizing Institution',
##            'help_text':  'Name of organization responsible for scanning. Will probably be the name of the partner.',
##            'max_length': 255,
##            'widget':     '',
##            'initial':    '',
##            'required':   True,
##        },
##        'default':    '',
##    },
##    {
##        'name':       'digitizing_date',
##        'xpath':      '',
##        'xpath_dup':  [],
##        'model_type': str,
##        'form_type':  forms.CharField,
##        'form': {
##            'label':      'Digitize Date',
##            'help_text':  'Date of scan. M/D/YYYY.',
##            'max_length': 255,
##            'widget':     '',
##            'initial':    '',
##            'required':   True,
##        },
##        'default':    '',
##    },
#    {
#        'name':       'credit',
#        'xpath':      '',
#        'xpath_dup':  [],
#        'model_type': str,
#        'form_type':  forms.CharField,
#        'form': {
#            'label':      'Credit Line',
#            'help_text':  'Short courtesy text relating to use of object.	Could identify either collection contributor and/or donor depending on deed of gift and/or usage agreement for object. Always begins with: "Courtesy of"',
#            'max_length': 255,
#            'widget':     '',
#            'initial':    '',
#            'required':   True,
#        },
#        'default':    '',
#    },
#    {
#        'name':       'rights',
#        'xpath':      '',
#        'xpath_dup':  [],
#        'model_type': str,
#        'form_type':  forms.CharField,
#        'form': {
#            'label':      'Rights and Restrictions',
#            'help_text':  'Short statement about usage limitations and intellectual property for the individual object. Only needs to be filled out if the individual object has restrictions different than those of the parent collection.',
#            'widget':     forms.Textarea,
#            'initial':    '',
#            'required':   False,
#        },
#        'default':    '',
#    },
    {
        'name':       'topic',
        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:subject/mods:topic/@xlink:href",
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
        'default':    '',
    },
    {
        'name':       'person',
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
        'default':    '',
    },
#    {
#        'name':       'notes',
#        'xpath':      "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:note/",
#        'xpath_dup':  [],
#        'model_type': str,
#        'form_type':  forms.CharField,
#        'form': {
#            'label':      'Notes',
#            'help_text':  '',
#            'widget':     forms.Textarea,
#            'initial':    '',
#            'required':   False,
#        },
#        'default':    '',
#    },
]


class MetsForm(XMLForm):
    def __init__(self, *args, **kwargs):
        super(MetsForm, self).__init__(*args, **kwargs)
    
    @staticmethod
    def process(xml, fields, form, namespaces=None):
        """Do things to the XML that I can't figure out how to do any other way.
        """
        xml = XMLForm.process(xml, fields, form, namespaces=namespaces)
        tree = etree.parse(StringIO.StringIO(xml))

        def getval(tree, namespaces, xpath):
            """Gets the first value; yes this is probably suboptimal
            """
            return tree.xpath(xpath, namespaces=namespaces)[0]
        
        def set_attr(tree, namespaces, xpath, attr, value):
            tag = tree.xpath(xpath, namespaces=namespaces)[0]
            tag.set(attr, value)
            return tree
        
        def set_tag_text(tree, namespaces, xpath, value):
            tag = getval(tree, namespaces, xpath)
            tag.text = value
            return tree
        
        def duplicate(tree, namespaces, src_xpath, dest_xpath):
            i = tree.xpath( src_xpath,  namespaces=namespaces )[0]
            tag = tree.xpath( dest_xpath, namespaces=namespaces )[0]
            tag.text = i
            return tree
        
        # created
        if not getval(tree, namespaces, "/mets:mets/mets:metsHdr/@CREATEDATE"):
            tree = set_attr(tree, namespaces,
                            "/mets:mets/mets:metsHdr", 'CREATEDATE',
                            datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))
        # modified
        tree = set_attr(tree, namespaces,
                        "/mets:mets/mets:metsHdr",
                        'LASTMODDATE',
                        datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))
        
        # fields
        
        # entity_id
        tree = duplicate(tree, namespaces,
                         "/mets:mets/@OBJID",
                         "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:identifier",
                         )
        # title
        tree = duplicate(tree, namespaces,
                         "/mets:mets/@LABEL",
                         "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:titleInfo/mods:title",
                         )
        
        # topic
        def process_topics(form, tree, namespaces):
            """
            TODO Add term to form so not necessary to hit Tematres server during save
                http://r020.com.ar/tematres/demo/xml.php?jsonTema=256|Lenguajes monomediales
                http://r020.com.ar/tematres/demo/xml.php?jsonTema=512|Telecomunicaciones
                http://r020.com.ar/tematres/demo/xml.php?jsonTema=1024|cell
            """
            #  <mods:subject>
            #    <mods:topic xlink:href=""></mods:topic>
            #  </mods:subject>
            xpath = "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:subject/mods:topic"
            
            form_urls = [t.strip() for t in form.cleaned_data['topic'].split(';')]
            topics = []
            # TODO Don't follow URLs for terms that have not changed.
            # TODO Cache tematres requests?
            terms = tematres.get_terms(form_urls)
            
            # remove existing tags
            parent = None
            for tag in tree.xpath(xpath, namespaces=NAMESPACES):
                parent = tag.getparent()
                parent.remove(tag)
            # replace with new tags
            for href,term in terms:
                tag_name  = xmlforms.expand_attrib_namespace('mods:topic', namespaces)
                attr_name = xmlforms.expand_attrib_namespace('xlink:href', namespaces)
                child = etree.Element(tag_name)
                child.set(attr_name, href)
                child.text = term
                parent.append(child)
            return tree
        
        tree = process_topics(form, tree, namespaces)

        return etree.tostring(tree, pretty_print=True)
