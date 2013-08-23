from copy import deepcopy

from django import forms
from django.conf import settings
from django.utils.datastructures import SortedDict

from ddrlocal.models.collection import COLLECTION_FIELDS
from ddrlocal.models.entity import ENTITY_FIELDS
from ddrlocal.models.files import FILE_FIELDS


class CollectionForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(CollectionForm, self).__init__(*args, **kwargs)
        fields = []
        for fkwargs in deepcopy(COLLECTION_FIELDS): # don't modify fields data
            # COLLECTION_FIELDS..files is not handled by CollectionForm
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


class EntityForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(EntityForm, self).__init__(*args, **kwargs)
        fields = []
        for fkwargs in deepcopy(ENTITY_FIELDS): # don't modify fields data
            # ENTITY_FIELDS..files is not handled by EntityForm
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


class FileForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(FileForm, self).__init__(*args, **kwargs)
        fields = []
        for fkwargs in deepcopy(FILE_FIELDS): # don't modify fields data
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
