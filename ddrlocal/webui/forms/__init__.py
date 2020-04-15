from copy import deepcopy
import logging
logger = logging.getLogger(__name__)
import os
import re
import traceback

from django import forms
from django.conf import settings
from django.utils.encoding import force_text

from DDR import modules
from webui.identifier import Identifier, INHERITABLE_FIELDS
from webui.util import OrderedDict

INTERVIEW_SIG_PATTERN = r'^denshovh-[a-z_0-9]{1,}-[0-9]{2,2}$'
INTERVIEW_SIG_REGEX = re.compile(INTERVIEW_SIG_PATTERN)


class LoginForm(forms.Form):
    username = forms.CharField(max_length=100)
    password = forms.CharField(widget=forms.PasswordInput)
    next = forms.CharField(max_length=255, required=False, widget=forms.HiddenInput)


class LoginOfflineForm(forms.Form):
    username = forms.CharField(max_length=100)
    email = forms.EmailField()
    git_name = forms.CharField(
        max_length=100, help_text='First name, last name'
    )
    next = forms.CharField(
        max_length=255, required=False, widget=forms.HiddenInput
    )


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
        self.fields = OrderedDict(fields)

class ObjectIDForm(forms.Form):
    """Accept new ID as text, check that it's a legal object ID
    
    given a parent object, we know what the children could be
    form:
    - radio btn to select child model
    - CharField for new ID
    display existing child under the form for reference
    on POST, check that
    - user input can be used to generate an Identifier
    - the identifier is of the specified model
    - the identifier's parent is the specified parent
    """
    model = forms.CharField(max_length=100, required=True, widget=forms.HiddenInput)
    parent_id = forms.CharField(max_length=100, required=True, widget=forms.HiddenInput)
    object_id = forms.CharField(max_length=100, required=True)

    def clean(self):
        """
        on POST, check that
        - user input can be used to generate an Identifier
        - the identifier is of the specified model
        - the identifier's parent is the specified parent
        """
        cleaned_data_copy = deepcopy(super(ObjectIDForm, self).clean())
        model = cleaned_data_copy['model']
        models = [model]
        # TODO hard-coded
        if model in ['entity','segment']:
            models = ['entity','segment']
        pid = cleaned_data_copy['parent_id']
        oid = cleaned_data_copy['object_id']
        try:
            pidentifier = Identifier(pid)
        except:
            raise forms.ValidationError(
                '"%s" is not a valid parent ID.' % pid
            )
        try:
            oidentifier = Identifier(oid)
        except:
            raise forms.ValidationError(
                '"%s" is not a valid object ID.' % oid
            )
        if oidentifier.model not in models:
            raise forms.ValidationError(
                '"%s" should be a %s but is a %s.' % (
                    oidentifier.id, model, oidentifier.model
                )
            )
        if oidentifier.parent_id() != pidentifier.id:
            raise forms.ValidationError(
                '"%s" parent should be %s but is %s.' % (
                    oidentifier.id,
                    pidentifier.id,
                    oidentifier.parent_id()
                )
            )
        # already exists
        if os.path.exists(oidentifier.path_abs('json')):
            raise forms.ValidationError(
                '"%s" already exists! Pick another ID' % (
                    oidentifier.id
                )
            )

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
        
        Tracebacks are added to a form.tracebacks dict so they can be
        printed in the page source.
        """
        # self.add_error modifies cleaned_data so work with copy
        cleaned_data_copy = deepcopy(super(DDRForm, self).clean())

        # Custom validation depends on having a FIELDS list in a module
        # object.  On the first stage of file import the user hasn't yet
        # decided which file to import.  We haven't calc'd the file hash
        # so we have no ID, no Identifier, and no module object.
        # Just give up. We'll validate later when they edit.
        if 'id' not in list(cleaned_data_copy.keys()):
            return
        
        try:
            obj = Identifier(cleaned_data_copy.pop('id')).object()
        except:
            raise forms.ValidationError(
                "Form data does not contain a valid object ID."
            )
        
        if settings.UTF8_STRICT:
            # per-field errors if can't convert to UTF-8
            for fieldname,value in cleaned_data_copy.items():
                if isinstance(value, str):
                    try:
                        data = value.decode('utf-8', 'strict')
                    except UnicodeError as err:
                        # attach error to field
                        unicode_hint = ''
                        start = getattr(err, 'start', None)
                        end = getattr(err, 'end', None)
                        if start is not None and end is not None:
                            unicode_hint = force_text(
                                err.object[max(start - 5, 0):min(end + 5, len(err.object))],
                                'ascii', errors='replace'
                            )
                        self.add_error(
                            fieldname,
                            'Text contains chars that cannot be converted to Unicode. "...%s..."' % unicode_hint
                        )
        
        # run form_post on field
        module = obj.identifier.fields_module()
        # put per-field error tracebacks here
        self.tracebacks = {}
        for fieldname,value in cleaned_data_copy.items():
            try:
                data = modules.Module(module).function(
                    'formpost_%s' % fieldname,
                    value
                )
            except Exception as err:
                # attach error to field
                self.add_error(fieldname, str(err))
                self.tracebacks[fieldname] = traceback.format_exc().strip()
            # can't validate signature_id without causing an import loop
            # so do it here
            # NOTE: field can contain a FILE ID or an interview signature img
            # TODO too much branching
            if (fieldname == 'signature_id') and value:
                # interview signature image
                # (ex. "denshovh-aart-03", "denshovh-hlarry_g-02")
                if 'denshovh' in value:
                    if INTERVIEW_SIG_REGEX.match(value):
                        continue
                    else:
                        self.add_error(
                            fieldname,
                            'Not a valid interview signature img (example: "denshovh-aart-03")'
                        )
                else:
                    # signature file
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
        # if field has children that inherit from it, add inherit-this checkbox
        if fkwargs.get('model') and fkwargs.get('name'):
            model_field = '.'.join([fkwargs['model'], fkwargs['name']])
            if model_field in INHERITABLE_FIELDS:
                helptext = "Apply value of %s to this object's children" % fkwargs['form']['label']
                #CHOICES = ((1, helptext),)
                #fobject = forms.ChoiceField(label='', choices=CHOICES,
                #                            widget=forms.CheckboxSelectMultiple,
                #                            required=False, initial=False)
                fobject = forms.BooleanField(label='', required=False, help_text=helptext)
                fields.append(('%s_inherit' % fkwargs['name'], fobject))
    fields = OrderedDict(fields)
    return fields
