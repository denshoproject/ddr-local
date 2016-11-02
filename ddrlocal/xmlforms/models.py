from copy import deepcopy
import StringIO

from lxml import etree

from xmlforms import tagtype, gettag, gettagvalue, settagvalue


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
            tag = gettag(tree, f['xpath'], self.namespaces)
            value = gettagvalue(tag, f.get('function',None))
            field = {'label': f['form']['label'],
                     'value': value,}
            setattr(self, f['name'], field)
            self.fieldnames.append(f['name'])
        
    @staticmethod
    def process(xml, fields, form):
        xml = XMLForm.process(xml, fields, form)
        tree = etree.parse(StringIO.StringIO(xml))
        return etree.tostring(tree, pretty_print=True)
    
    def labels_values(self):
        return [getattr(self, fname, '') for fname in self.fieldnames]
