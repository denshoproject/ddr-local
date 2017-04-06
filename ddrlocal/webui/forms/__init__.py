from copy import deepcopy
import logging
logger = logging.getLogger(__name__)

from django import forms
from django.conf import settings
from django.utils.datastructures import SortedDict

from DDR import modules
from webui.identifier import Identifier


class LoginForm(forms.Form):
    username = forms.CharField(max_length=100)
    password = forms.CharField(widget=forms.PasswordInput)
    next = forms.CharField(max_length=255, required=False, widget=forms.HiddenInput)


class TaskDismissForm( forms.Form ):
    next = forms.CharField(max_length=255, required=False, widget=forms.HiddenInput)
    
    def __init__( self, *args, **kwargs ):
        celery_tasks = kwargs.pop('celery_tasks')
        super(TaskDismissForm, self).__init__(*args, **kwargs)
        fields = [
            ('next', self.fields['next'])
        ]
        for task in celery_tasks:
            if task.get('task_id', None) and task.get('dismissable', None):
                fields.append(
                    ('dismiss_%s' % task['task_id'], forms.BooleanField(required=False))
                )
            else:
                fields.append(
                    ('greyed_%s' % task['task_id'], forms.BooleanField(required=False))
                )
        # Django Form object takes a SortedDict rather than list
        self.fields = SortedDict(fields)


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
        self.fields = construct_form(deepcopy(MODEL_FIELDS))

    def clean(self):
        """Run form_post on each field and report errors.
        
        This instead of just crashing the page. :)
        Do each field separately so errors are attached to the individual
        form fields.
        """
        # self.add_error modifies cleaned_data so work with copy
        cleaned_data_copy = deepcopy(super(DDRForm, self).clean())
        
        
        try:
            obj = Identifier(cleaned_data_copy.pop('id')).object()
        except:
            raise forms.ValidationError(
                "Form data does not contain a valid object ID."
            )
        # run form_post on field
        module = obj.identifier.fields_module()
        for fieldname,value in cleaned_data_copy.iteritems():
            try:
                data = modules.Module(module).function(
                    'formpost_%s' % fieldname,
                    value
                )
            except Exception as err:
                # attach error to field
                self.add_error(fieldname, str(err))
            # can't validate signature_id without causing an import loop
            # so do it here
            if fieldname == 'signature_id':
                si = None
                try:
                    si = Identifier(id=value)
                except:
                    self.add_error(fieldname, 'Not a valid object ID')
                if si and not (si.model == 'file'):
                    self.add_error(fieldname, 'Only files can be used as signatures.')


def construct_form(model_fields):
    fields = []
    for fkwargs in model_fields: # don't modify fields data
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
        # if field is inheritable, add inherit-this checkbox
        if fkwargs.get('inheritable', None):
            helptext = "Apply value of %s to this object's children" % fkwargs['form']['label']
            #CHOICES = ((1, helptext),)
            #fobject = forms.ChoiceField(label='', choices=CHOICES,
            #                            widget=forms.CheckboxSelectMultiple,
            #                            required=False, initial=False)
            fobject = forms.BooleanField(label='', required=False, help_text=helptext)
            fields.append(('%s_inherit' % fkwargs['name'], fobject))
    # Django Form object takes a SortedDict rather than list
    fields = SortedDict(fields)
    return fields
