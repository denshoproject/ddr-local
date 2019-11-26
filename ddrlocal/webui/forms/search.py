import logging
logger = logging.getLogger(__name__)
import os

from django import forms
from django.conf import settings

from webui import docstore
from webui import search
from ..util import OrderedDict


class SearchForm(forms.Form):
    field_order = search.SEARCH_PARAM_WHITELIST
    search_results = None
    
    def __init__( self, *args, **kwargs ):
        if kwargs.get('search_results'):
            self.search_results = kwargs.pop('search_results')
        super(SearchForm, self).__init__(*args, **kwargs)
        self.fields = self.construct_form(self.search_results)

    def construct_form(self, search_results):
        fields = [
            (
                'fulltext',
                forms.CharField(
                    max_length=255,
                    required=False,
                    widget=forms.TextInput(
                        attrs={
                            'id': 'id_query',
                            'class': 'form-control',
                            'placeholder': 'Search...',
                        }
                    ),
                )
            ),
            (
                'parent',
                forms.CharField(
                    max_length=255,
                    required=False,
                    widget=forms.TextInput(
                        attrs={
                            'id': 'id_parent',
                        }
                    ),
                )
            ),
            (
                'models',
                forms.MultipleChoiceField(
                    label='Models',
                    choices=[(model,model) for model in search.SEARCH_MODELS],
                    required=False,
                )
            ),
        ]
        
        # fill in options and doc counts from aggregations
        if search_results and search_results.aggregations:
            for fieldname in search_results.aggregations.keys():
                choices = [
                    (
                        item['key'],
                        '%s (%s)' % (item['label'], item['doc_count'])
                    )
                    for item in search_results.aggregations[fieldname]
                ]
                if choices:
                    fields.append((
                        fieldname,
                        forms.MultipleChoiceField(
                            label=search.SEARCH_FORM_LABELS.get(
                                fieldname, fieldname),
                            choices=choices,
                            required=False,
                        ),
                    ))
        
        # Django Form object takes an OrderedDict rather than list
        fields = OrderedDict(fields)
        return fields
