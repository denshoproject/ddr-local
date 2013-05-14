from datetime import datetime, date
from copy import deepcopy
import StringIO

from lxml import etree

from django import forms
from django.utils.datastructures import SortedDict




def _tag_type(tag):
    """some of these checks cause errors for some reason
    """
    try:
        if tag.is_text:
            return 'text'
    except:
        pass
    try:
        if tag.is_attribute:
            return 'attribute'
    except:
        pass
    try:
        if tag.is_tail:
            return 'tail'
    except:
        pass
    return 'unknown'


class XMLForm(forms.Form):
    """
    Fields data structure:
        EXAMPLE_FIELDS = [
            {
                'name':       'field1',
                'xpath':      '/path/to/char/field',
                'model_type': str,
                'form_type':  forms.CharField,
                'form': {
                    'label':     'Field 1',
                    'help_text': 'Help text for form.',
                    'max_length' :255,
                    'widget':    '',
                    'initial':   'Initial data',
                    'required':  False,
                },
                'default':    '',
            },
            {
                'name':       'field2',
                'xpath':      '/path/to/date/field',
                'model_type': datetime.date,
                'form_type':  forms.DateField,
                'form': {
                    'label':    'Field 2',
                    'help_text': 'This is a date (YYYY-MM-DD)',
                    'widget':   '',
                    'initial':  '',
                    'required': True,
                },
                'default':    '1970-1-1',
            },
            {
                'name':       'field3',
                'xpath':      '/path/to/textarea/field',
                'model_type': str,
                'form_type':  forms.CharField,
                'form': {
                    'label':     'Field 3',
                    'help_text': 'This is a textarea.',
                    'widget':    forms.Textarea,
                    'initial':   '',
                    'required':  False,
                },
                'default':    '',
            },
            {
                'name':       'field4',
                'xpath':      '/path/to/attribute/field/@attr',
                'model_type': str,
                'form_type':  forms.ChoiceField,
                'form': {
                    'label':     'Field 4',
                    'help_text': 'Choose from one of the choices.',
                    'choices':   CHOICES_LIST,
                    'widget':    '',
                    'initial':   '',
                    'required':  True,
                },
                'default':    'default',
            },
        ]
    """
    
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
            # instantiate Field object and to list
            ftype = fkwargs['form_type']
            fobject = ftype(*fargs, **fkwargs['form'])
            fields.append((fkwargs['name'], fobject))
        # Django Form object takes a SortedDict rather than list
        self.fields = SortedDict(fields)
    
    @staticmethod
    def prep_fields(fields, xml):
        """Takes raw kwargs, fills in initial data from xml file.
        
        kwargs[*]['initial'] is used to populate form fields
        
        @param fields: Dict data structure representing fields.
        @param xml: String representation of an XML document.
        @return: fields, with initial data added.
        """
        thistree = etree.parse(StringIO.StringIO(xml))
        for f in fields:
            # find tags, get first one
            tag = None
            tags = thistree.xpath(f['xpath'])
            if tags and len(tags):
                if (type(tags) == type([])):
                    tag = tags[0]
                else:
                    tag = tags
            # tag text, attribute, or tail
            tagtype = _tag_type(tag)
            if hasattr(tag, 'text'):
                initial = tag.text
            elif type(tag) == type(''):
                initial = tag
            elif tagtype == 'attribute':
                attr = f['xpath'].split('@')[1]
                initial = tag.getparent().attrib[attr]
            else:
                initial = None
            # insert into form data
            if initial:
                f['form']['initial'] = initial.strip()
        return fields
        
    @staticmethod
    def process(xml, fields, form):
        """Writes form.cleaned_data values to XML
        
        Uses XPaths from field_kwargs
        
        @param xml: String representation of an XML document.
        @param fields: Dict data structure representing fields.
        @return: XML document string
        """
        tree = etree.parse(StringIO.StringIO(xml))
        for f in deepcopy(fields):
            cleaned_data = form.cleaned_data[f['name']]
            # non-string data
            if type(cleaned_data) == type(datetime(1970,1,1, 1,1,1)):
                cleaned_data = cleaned_data.strftime('%Y-%m-%d %H:%M:%S')
            elif type(cleaned_data) == type(date(1970,1,1)):
                cleaned_data = cleaned_data.strftime('%Y-%m-%d')
            # find tags, get first one
            tags = tree.xpath(f['xpath'])
            if tags and len(tags):
                if (type(tags) == type([])):
                    tag = tags[0]
                else:
                    tag = tags
            # tag text, attribute, or tail
            tagtype = _tag_type(tag)
            if hasattr(tag, 'text'):
                tag.text = cleaned_data
            elif type(tag) == type(''):
                tag = cleaned_data
            elif tagtype == 'attribute':
                attr = f['xpath'].split('@')[1]
                tag.getparent().attrib[attr] = cleaned_data
        return etree.tostring(tree, pretty_print=True)
