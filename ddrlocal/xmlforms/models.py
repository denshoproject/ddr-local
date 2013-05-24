from datetime import datetime, date
from copy import deepcopy
import StringIO

from lxml import etree

from xmlforms.forms import _tag_type


class XMLModel(object):
    """
    uses same FIELDS data structure as XMLForm
    
    give it the same set of fields
    and an xml string
    
    generates a Python object that can be used in templates
    """

    def __init__(self, *args, **kwargs):
        xml = args[0]
        fields = args[1]
        #super(XMLModel, self).__init__(*args, **kwargs)
        tree = etree.parse(StringIO.StringIO(xml))
        for f in fields:
            # find tags, get first one
            tag = None
            tags = tree.xpath(f['xpath'])
            if tags and len(tags):
                if (type(tags) == type([])):
                    tag = tags[0]
                else:
                    tag = tags
            # tag text, attribute, or tail
            tagtype = _tag_type(tag)
            if hasattr(tag, 'text'):
                value = tag.text
            elif type(tag) == type(''):
                value = tag
            elif tagtype == 'attribute':
                attr = f['xpath'].split('@')[1]
                value = tag.getparent().attrib[attr]
            else:
                value = None
            # insert into object
            field = {'label': f['form']['label'],
                     'value': value,}
            setattr(self, f['name'], field)
    
    @staticmethod
    def process(xml, fields, form):
        xml = XMLForm.process(xml, fields, form)
        tree = etree.parse(StringIO.StringIO(xml))
        return etree.tostring(tree, pretty_print=True)
