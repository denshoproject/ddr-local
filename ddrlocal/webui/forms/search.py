from collections import OrderedDict
import logging
logger = logging.getLogger(__name__)

from django import forms
from django.conf import settings
from django.core.cache import cache

from webui import models
from webui.models import docstore


# Pretty labels for multiple choice fields
# (After initial search the choice lists come from search aggs lists
# which only include IDs and doc counts.)
# {
#     'topics': {
#         '1': u'Immigration and citizenship',
#         ...
#     },
#     'facility: {...},
# }
FORMS_CHOICE_LABELS = {}

def forms_choice_labels():
    """Lazy-load and keep human-readable labels for form choices
    
    TODO Would be better to generate dicts from ES data than densho-vocabs
    """
    global FORMS_CHOICE_LABELS
    if not FORMS_CHOICE_LABELS:
        ds = docstore.DocstoreManager(
            models.INDEX_PREFIX, settings.DOCSTORE_HOST, settings
        )
        forms_choices = ds.es.get(
            index='ddrforms',
            id='forms-choices'
        )['_source']
        for key in forms_choices.keys():
            field = key.replace('-choices','')
            FORMS_CHOICE_LABELS[field] = {
                c[0].split('-')[1]: c[1]
                for c in forms_choices[key]
            }
    return FORMS_CHOICE_LABELS


class SearchForm(forms.Form):
    field_order = models.SEARCH_PARAM_WHITELIST
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
                    choices=[(model,model) for model in models.SEARCH_MODELS],
                    required=False,
                )
            ),
        ]
        
        # fill in options and doc counts from aggregations
        if search_results and search_results.aggregations:
            choice_labels = forms_choice_labels()
            for fieldname,aggs in search_results.aggregations.items():
                choices = []
                for item in aggs:
                    if hasattr(item, 'key') and item['key']:
                        label = choice_labels[fieldname][item['key']]
                        choice = (
                            item['key'],
                            '%s (%s)' % (label, item['doc_count'])
                        )
                        choices.append(choice)
                if choices:
                    fields.append((
                        fieldname,
                        forms.MultipleChoiceField(
                            label=models.SEARCH_FORM_LABELS.get(
                                fieldname, fieldname),
                            choices=choices,
                            required=False,
                        ),
                    ))
        
        # Django Form object takes an OrderedDict rather than list
        fields = OrderedDict(fields)
        return fields
