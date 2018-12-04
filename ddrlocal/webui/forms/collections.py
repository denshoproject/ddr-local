import logging
logger = logging.getLogger(__name__)

from django import forms

class NewCollectionForm(forms.Form):
    repo = forms.CharField(max_length=100)  # TODO should be disabled/non-editable
    org = forms.CharField(max_length=100)  # TODO should be disabled/non-editable
    cid = forms.IntegerField()

class UpdateForm(forms.Form):
    xml = forms.CharField(widget=forms.Textarea)

class SyncConfirmForm(forms.Form):
    confirmed = forms.BooleanField(
        help_text='Yes, I want to synchronize this collection.'
    )

class SignaturesConfirmForm(forms.Form):
    confirmed = forms.BooleanField(
        help_text='Yes, I want to choose signatures for this collection.'
    )

class UploadFileForm(forms.Form):
    file = forms.FileField()
