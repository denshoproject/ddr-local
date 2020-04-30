import logging
logger = logging.getLogger(__name__)

from django import forms


class JSONForm(forms.Form):
    json = forms.CharField(widget=forms.Textarea)

class UpdateForm(forms.Form):
    xml = forms.CharField(widget=forms.Textarea)

class DeleteEntityForm(forms.Form):
    confirmed = forms.BooleanField(help_text='Yes, I really want to delete this object.')

class RmDuplicatesForm(forms.Form):
    confirmed = forms.BooleanField(help_text='Yes, remove the duplicates.')
