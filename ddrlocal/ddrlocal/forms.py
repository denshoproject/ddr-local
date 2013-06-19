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
            fargs = []
            # instantiate Field object and to list
            ftype = fkwargs['form_type']
            form_kwargs = fkwargs['form']
            fobject = ftype(*fargs, **form_kwargs)
            fields.append((fkwargs['name'], fobject))
        # Django Form object takes a SortedDict rather than list
        self.fields = SortedDict(fields)
