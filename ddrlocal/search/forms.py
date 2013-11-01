import os

from django import forms


class IndexConfirmForm(forms.Form):
    confirm = forms.BooleanField(label=None, help_text='Re-index collections')

class DropConfirmForm(forms.Form):
    confirm = forms.BooleanField(label=None, help_text='Drop indexes')
