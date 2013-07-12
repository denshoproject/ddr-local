from django import forms
from django.conf import settings

class AddFileForm(forms.Form):
    role = forms.ChoiceField(choices=settings.ENTITY_FILE_ROLES)
    file = forms.FileField()

class EditFileForm(forms.Form):
    sha1 = forms.CharField(max_length=100)
    sort = forms.IntegerField()
    role = forms.ChoiceField(choices=settings.ENTITY_FILE_ROLES)
    label = forms.CharField(max_length=255)
