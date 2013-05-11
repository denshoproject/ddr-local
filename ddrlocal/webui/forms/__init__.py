from copy import deepcopy
import StringIO

from lxml import etree

from django import forms
from django.utils.datastructures import SortedDict



class LoginForm(forms.Form):
    git_name = forms.CharField(max_length=100)
    git_mail = forms.EmailField()
    username = forms.CharField(max_length=100)
    password = forms.CharField(widget=forms.PasswordInput)



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
