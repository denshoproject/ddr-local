import os

from django import forms
from django.conf import settings

from ddrlocal.models.files import PERMISSIONS_CHOICES

def shared_folder_files():
    d = settings.VIRTUALBOX_SHARED_FOLDER
    files = []
    for f in os.listdir(d):
        fabs = os.path.join(d,f)
        if not os.path.isdir(fabs):
            files.append( (fabs,f) )
    return files
            

class NewFileForm(forms.Form):
    public = forms.ChoiceField(choices=PERMISSIONS_CHOICES)
    #path = forms.FilePathField(path=settings.VIRTUALBOX_SHARED_FOLDER)
    path = forms.ChoiceField(choices=shared_folder_files(), required=False)
    role = forms.ChoiceField(choices=settings.ENTITY_FILE_ROLES)
    label = forms.CharField(max_length=255, required=False)
    sort = forms.IntegerField()
    
    def __init__(self, *args, **kwargs):
        path_choices = None
        if kwargs.has_key('path_choices'):
            path_choices = kwargs.pop('path_choices')
        super(NewFileForm, self).__init__(*args, **kwargs)
        if path_choices:
            self.fields['path'].choices = path_choices

class EditFileForm(forms.Form):
    label = forms.CharField(max_length=255, required=False)
    sort = forms.IntegerField()
    xmp = forms.CharField(widget=forms.Textarea, required=False)

class NewAccessFileForm(forms.Form):
    path = forms.CharField(max_length=255, widget=forms.HiddenInput)
