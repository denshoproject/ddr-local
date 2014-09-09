import logging
logger = logging.getLogger(__name__)
import os
import sys

from django import forms
from django.conf import settings

if settings.REPO_MODELS_PATH not in sys.path:
    sys.path.append(settings.REPO_MODELS_PATH)
try:
    # TODO This module should not have to import these!
    from repo_models.files import PERMISSIONS_CHOICES, RIGHTS_CHOICES
except ImportError:
    from ddrlocal.models.files import PERMISSIONS_CHOICES, RIGHTS_CHOICES

def shared_folder_files():
    d = settings.VIRTUALBOX_SHARED_FOLDER
    files = []
    for f in os.listdir(d):
        fabs = os.path.join(d,f)
        if not os.path.isdir(fabs):
            files.append( (fabs,f) )
    return files
            

class NewFileForm(forms.Form):
    public = forms.ChoiceField(choices=PERMISSIONS_CHOICES, required=True, label='Privacy Level', help_text='Whether this file should be accessible from the public website.')
    rights = forms.ChoiceField(choices=RIGHTS_CHOICES, label='Rights', required=True, help_text='The use license for this file.')
    #path = forms.FilePathField(path=settings.VIRTUALBOX_SHARED_FOLDER)
    #path = forms.ChoiceField(choices=shared_folder_files(), required=False)
    path = forms.CharField(max_length=255, widget=forms.HiddenInput)
    role = forms.ChoiceField(choices=settings.ENTITY_FILE_ROLES)
    label = forms.CharField(max_length=255, required=False)
    sort = forms.IntegerField(label='Sort Order', initial=1, help_text='Order of this file in relation to others for this object (ordered low to high). Can be used to arrange images in a multi-page document.')
    
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

class DeleteFileForm(forms.Form):
    confirmed = forms.BooleanField(help_text='Yes, I really want to delete this file.')
