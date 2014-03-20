import logging
logger = logging.getLogger(__name__)
import os

from django import forms
from django.conf import settings

class SearchForm(forms.Form):
    query = forms.CharField(max_length=255)

class IndexConfirmForm(forms.Form):
    confirm = forms.BooleanField(label=None, help_text='Re-index collections')

class DropConfirmForm(forms.Form):
    confirm = forms.BooleanField(label=None, help_text='Drop indexes')
