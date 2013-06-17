from copy import deepcopy

from django import forms
from django.conf import settings

from ddrlocal.models import METS_FIELDS


class EntityForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(EntityForm, self).__init__(*args, **kwargs)
        fields = []
        for fkwargs in deepcopy(METS_FIELDS): # don't modify fields data
            fargs = []
            # instantiate Field object and to list
            ftype = fkwargs['form_type']
            fobject = ftype(*fargs, **fkwargs['form'])
            fields.append((fkwargs['name'], fobject))
        # Django Form object takes a SortedDict rather than list
        self.fields = SortedDict(fields)
