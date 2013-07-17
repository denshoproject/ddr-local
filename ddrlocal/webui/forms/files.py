from django import forms
from django.conf import settings

class NewFileForm(forms.Form):
    role = forms.ChoiceField(choices=settings.ENTITY_FILE_ROLES)
    path = forms.FilePathField(path=settings.VIRTUALBOX_SHARED_FOLDER)

class EditFileForm(forms.Form):
    sort = forms.IntegerField()
    role = forms.ChoiceField(choices=settings.ENTITY_FILE_ROLES)
    label = forms.CharField(max_length=255)
    exif = forms.CharField(widget=forms.Textarea, required=False)
