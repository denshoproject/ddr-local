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

MIMETYPE_CHOICES = [
    ('text/html', 'text/html'),
    ('application/pdf', 'application/pdf'),
    ('video/mpg', 'video/mpg'),
    ('video/mp4', 'video/mp4'),
    ('video/ogg', 'video/ogg'),
    ('video/x-m4v', 'video/x-m4v'),
    ('video/x-msvideo', 'video/x-msvideo'),
    ('video/quicktime', 'video/quicktime'),
    ('application/mxf', 'application/mxf'),
    ('audio/mp3', 'audio/mp3'),
    ('audio/x-wav', 'audio/x-wav'),
    ('audio/mp4', 'audio/mp4'),
    ('audio/ogg', 'audio/ogg'),
    ('image/tiff', 'image/tiff'),
    ('image/jpeg', 'image/jpeg'), 
    ('image/bmp', 'image/bmp')
]

class NewExternalFileForm(forms.Form):
    filename = forms.CharField(required=True, max_length=255)
    mimetype = forms.ChoiceField(choices=MIMETYPE_CHOICES, required=True)
    size = forms.CharField(required=True, max_length=255)
    sha1 = forms.CharField(required=True, max_length=255)
    md5 = forms.CharField(required=True, max_length=255)
    sha256 = forms.CharField(required=True, max_length=255)

class NewMetaFileForm(forms.Form):
    sha1 = forms.CharField(max_length=255)
    filename = forms.CharField(max_length=255)

class NewAccessFileForm(forms.Form):
    path = forms.CharField(max_length=255, widget=forms.HiddenInput)

class DeleteFileForm(forms.Form):
    confirmed = forms.BooleanField(help_text='Yes, I really want to delete this file.')
