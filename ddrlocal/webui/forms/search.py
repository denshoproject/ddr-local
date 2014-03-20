import logging
logger = logging.getLogger(__name__)

from django import forms
from django.conf import settings

class SearchForm(forms.Form):
    query = forms.CharField(max_length=255)
