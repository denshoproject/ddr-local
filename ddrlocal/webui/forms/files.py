from django import forms
from django.conf import settings

class AddFileForm(forms.Form):
    role = forms.ChoiceField(choices=settings.ENTITY_FILE_ROLES)
    file = forms.FileField()
