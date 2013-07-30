from copy import deepcopy

from django import forms
from django.conf import settings
from django.utils.datastructures import SortedDict

from ddrlocal.models.collection import COLLECTION_FIELDS
from ddrlocal.models.entity import ENTITY_FIELDS


class CollectionForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(CollectionForm, self).__init__(*args, **kwargs)
        fields = []
        for fkwargs in deepcopy(COLLECTION_FIELDS): # don't modify fields data
            # COLLECTION_FIELDS..files is not handled by CollectionForm
            if fkwargs.get('form', None):
                # instantiate Field object and to list
                form_field_object = fkwargs['form_type']
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
            if fkwargs.get('form', None):
                # instantiate Field object and to list
                form_field_object = fkwargs['form_type']
                fobject = form_field_object(*[], **fkwargs['form'])
                fields.append((fkwargs['name'], fobject))
                # Django Form object takes a SortedDict rather than list
                self.fields = SortedDict(fields)
