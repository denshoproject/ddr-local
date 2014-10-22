import logging
logger = logging.getLogger(__name__)
import os
import sys

from django import forms
from django.conf import settings

from webui.forms import DDRForm

def shared_folder_files():
    d = settings.VIRTUALBOX_SHARED_FOLDER
    files = []
    for f in os.listdir(d):
        fabs = os.path.join(d,f)
        if not os.path.isdir(fabs):
            files.append( (fabs,f) )
    return files
            
class NewFileDDRForm(DDRForm):
    
    def __init__(self, *args, **kwargs):
        path_choices = None
        if kwargs.has_key('path_choices'):
            path_choices = kwargs.pop('path_choices')
        super(NewFileDDRForm, self).__init__(*args, **kwargs)
        if path_choices:
            self.fields['path'].choices = path_choices

class NewAccessFileForm(forms.Form):
    path = forms.CharField(max_length=255, widget=forms.HiddenInput)

class DeleteFileForm(forms.Form):
    confirmed = forms.BooleanField(help_text='Yes, I really want to delete this file.')
