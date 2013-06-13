from datetime import datetime, date
from copy import deepcopy
import StringIO

from lxml import etree

from django import forms
from django.utils.datastructures import SortedDict

from xmlforms import tagtype, gettag, gettagvalue, settagvalue



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
    namespaces = None
    
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
        if kwargs.has_key('namespaces'):
            self.namespaces = kwargs.pop('namespaces')
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
    def prep_fields(fields, xml, namespaces=None):
        """Takes raw kwargs, fills in initial data from xml file.
        
        kwargs[*]['initial'] is used to populate form fields
        
        @param fields: Dict data structure representing fields.
        @param xml: String representation of an XML document.
        @return: fields, with initial data added.
        """
        thistree = etree.parse(StringIO.StringIO(xml))
        for f in fields:
            tag = gettag(thistree, f['xpath'], namespaces)
            value = gettagvalue(tag)
            # insert into form data
            if value:
                f['form']['initial'] = value
        return fields
        
    @staticmethod
    def process(xml, fields, form, namespaces=None):
        """Writes form.cleaned_data values to XML
        
        Uses XPaths from field_kwargs
        
        @param xml: String representation of an XML document.
        @param fields: Dict data structure representing fields.
        @return: XML document string
        """
        tree = etree.parse(StringIO.StringIO(xml))
        for f in deepcopy(fields):
            cleaned_data = form.cleaned_data[f['name']]
            
            # datetime
            if type(cleaned_data)   == type(datetime(1970,1,1, 1,1,1)):
                cleaned_data = cleaned_data.strftime('%Y-%m-%d %H:%M:%S')
            
            # date
            elif type(cleaned_data) == type(date(1970,1,1)):
                cleaned_data = cleaned_data.strftime('%Y-%m-%d')
            
            tag = gettag(tree, f['xpath'], namespaces)
            tag = settagvalue(tag, f['xpath'], cleaned_data, namespaces)
        return etree.tostring(tree, pretty_print=True)
