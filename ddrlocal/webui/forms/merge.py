import logging
logger = logging.getLogger(__name__)

from django import forms
from webui.util import OrderedDict


class MergeCommitForm(forms.Form):
    which = forms.CharField(max_length=255, widget=forms.HiddenInput)
    path = forms.CharField(max_length=255, widget=forms.HiddenInput)

class MergeRawForm(forms.Form):
    filename = forms.CharField(max_length=255, widget=forms.HiddenInput)
    text = forms.CharField(widget=forms.Textarea)

class MergeJSONForm(forms.Form):
    filename = forms.CharField(max_length=255, widget=forms.HiddenInput)
    
    def __init__(self, *args, **kwargs):
        if kwargs.has_key('fields'):
            field_kwargs = kwargs.pop('fields')
        else:
            field_kwargs = []
        super(MergeJSONForm, self).__init__(*args, **kwargs)
        fields = []
        for f in field_kwargs:
            fields.append(('%s_left' % f['name'], forms.CharField(widget=forms.Textarea)))
            fields.append(('%s_right' % f['name'], forms.CharField(widget=forms.Textarea)))
            fields.append(('%s_choose' % f['name'],
                          forms.ChoiceField(choices=['left','right'], widget=forms.RadioSelect, required=True)))
        self.fields = OrderedDict(fields)
