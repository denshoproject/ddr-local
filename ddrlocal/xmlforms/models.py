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
    namespaces = None
    
    def __init__(self, *args, **kwargs):
        xml = args[0]
        fields = args[1]
        if kwargs.has_key('namespaces'):
            self.namespaces = kwargs.pop('namespaces')
        #super(XMLModel, self).__init__(*args, **kwargs)
        tree = etree.parse(StringIO.StringIO(xml))
        self.fieldnames = []
        for f in fields:
            tag = XMLModel._gettag(tree, f['xpath'], self.namespaces)
            value = XMLModel._gettagvalue(tag)
            field = {'label': f['form']['label'],
                     'value': value,}
            setattr(self, f['name'], field)
            self.fieldnames.append(f['name'])
    
    @staticmethod
    def _gettag(tree, xpath, namespaces):
        """
        TODO Refactor this!!!
        For each field, only the first tag is retrieved, when there may be many that we are interested in.
        """
        tag = None
        tags = tree.xpath(xpath, namespaces=namespaces)
        if tags and len(tags):
            if (type(tags) == type([])):
                tag = tags[0]
            else:
                tag = tags
        return tag

    @staticmethod
    def _gettagvalue(tag):
        """Gets tag text, attribute, or tail, depending on the xpath
        """
        value = None
        tagtype = _tag_type(tag)
        if type(tag) == type(etree._ElementStringResult()):
            value = tag
        elif hasattr(tag, 'text'):
            value = tag.text
        elif type(tag) == type(''):
            value = tag
        elif tagtype == 'attribute':
            attr = f['xpath'].split('@')[1]
            value = tag.getparent().attrib[attr]
        # strip before/after whitespace
        try:
            value = value.strip()
        except:
            pass
        return value
    
    @staticmethod
    def process(xml, fields, form):
        xml = XMLForm.process(xml, fields, form)
        tree = etree.parse(StringIO.StringIO(xml))
        return etree.tostring(tree, pretty_print=True)
    
    def labels_values(self):
        return [getattr(self, fname, '') for fname in self.fieldnames]
