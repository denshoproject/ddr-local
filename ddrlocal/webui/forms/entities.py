from django import forms
from django.conf import settings

class NewEntityForm(forms.Form):
    eid = forms.CharField(max_length=100)

class UpdateForm(forms.Form):
    xml = forms.CharField(widget=forms.Textarea)

class AddFileForm(forms.Form):
    role = forms.ChoiceField(choices=settings.ENTITY_FILE_ROLES)
    file = forms.FileField()
