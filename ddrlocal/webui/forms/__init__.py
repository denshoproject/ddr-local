from copy import deepcopy
import logging
logger = logging.getLogger(__name__)

from django import forms
from django.conf import settings
from django.utils.datastructures import SortedDict



class LoginForm(forms.Form):
    username = forms.CharField(max_length=100)
    password = forms.CharField(widget=forms.PasswordInput)
    next = forms.CharField(max_length=255, required=False, widget=forms.HiddenInput)

class TaskDismissForm(forms.Form):
    next = forms.CharField(max_length=255, required=False, widget=forms.HiddenInput)

class DDRForm(forms.Form):
    def __init__(self, *args, **kwargs):
        """Build a form from a *_FIELDS data structure.
        
        Each field must contain a "form_type" and a "form".
        
        The field's "form_type" must match one of Django's built-in Field classes.
        ("model_type" indicates Python data type to use in object.)
        
        The field's "form" dict must contain legal kwargs for the Django Field
        class indicated by "form_type".  The exception is that ['form']['widget']
        must be a String rather than an actual Django widget object.
        
        This function steps through *_FIELDS.
        For each field it instantiates the Django Field object specified in "form_type",
        passes in the arguments in "form", and adds the field object to the form's
        "fields" attribute.
        
        @param fields
        """
        if kwargs.get('fields', None):
            MODEL_FIELDS = kwargs.pop('fields')
        else:
            MODEL_FIELDS = []
        
        super(DDRForm, self).__init__(*args, **kwargs)
        
        fields = []
        for fkwargs in deepcopy(MODEL_FIELDS): # don't modify fields data
            
            if fkwargs.get('form', None) and fkwargs.get('form_type', None):
                
                # replace widget name with widget object
                if fkwargs['form'].get('widget', None):
                    widget_name = fkwargs['form']['widget']
                    if hasattr(forms, widget_name):
                        fkwargs['form']['widget'] = getattr(forms, widget_name)
                
                # instantiate Field object and to list
                field_name = fkwargs['form_type']
                if hasattr(forms, field_name):
                    form_field_object = getattr(forms, field_name)
                    fobject = form_field_object(*[], **fkwargs['form'])
                    fields.append((fkwargs['name'], fobject))
        
        # Django Form object takes a SortedDict rather than list
        self.fields = SortedDict(fields)
