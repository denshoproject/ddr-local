import logging
logger = logging.getLogger(__name__)
import os

from django import forms
from django.conf import settings

from DDR.docstore import index_names, index_exists, make_index_name
from webui import set_docstore_index


class SearchForm(forms.Form):
    query = forms.CharField(max_length=255)


def _index_choices( request, show_missing=False ):
    # current indices in Elasticsearch
    indices = []
    for index in index_names(settings.DOCSTORE_HOSTS):
        indices.append(index)
    if show_missing:
        # session index
        session_index = None
        if request:
            set_docstore_index(request)
            session_index = request.session.get('docstore_index', None)
            if session_index and (session_index not in indices):
                indices.append(session_index)
        # if current storage has no index
        storage_label = request.session.get('storage_label', None)
        if request and storage_label:
            if storage_label:
                store_index = make_index_name(storage_label)
                if store_index and (store_index not in indices):
                    indices.append(store_index)
    # make list of tuples for choices menu
    return [(index,index) for index in indices]

class IndexConfirmForm(forms.Form):
    index = forms.ChoiceField(choices=[])
    
    def __init__(self, *args, **kwargs):
        if kwargs.get('request', None):
            request = kwargs.pop('request')
        else:
            request = None
        super(IndexConfirmForm, self).__init__(*args, **kwargs)
        # add current index to list
        if request:
            self.fields['index'].choices = _index_choices(request, show_missing=True)

class DropConfirmForm(forms.Form):
    index = forms.ChoiceField(choices=[])
    confirm = forms.BooleanField(label=None, help_text='I really want to do this')
    
    def __init__(self, *args, **kwargs):
        if kwargs.get('request', None):
            request = kwargs.pop('request')
        else:
            request = None
        super(DropConfirmForm, self).__init__(*args, **kwargs)
        # add current index to list
        if request:
            self.fields['index'].choices = _index_choices(request)
