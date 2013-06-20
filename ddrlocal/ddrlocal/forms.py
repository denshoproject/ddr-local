from copy import deepcopy

from django import forms
from django.conf import settings
from django.utils.datastructures import SortedDict

from ddrlocal.models.entity import METS_FIELDS


class EntityForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(EntityForm, self).__init__(*args, **kwargs)
        fields = []
        for fkwargs in deepcopy(METS_FIELDS): # don't modify fields data
            # METS_FIELDS..files is not handled by EntityForm
            if fkwargs.get('form', None):
                # instantiate Field object and to list
                form_field_object = fkwargs['form_type']
                fobject = form_field_object(*[], **fkwargs['form'])
                fields.append((fkwargs['name'], fobject))
                # Django Form object takes a SortedDict rather than list
                self.fields = SortedDict(fields)
