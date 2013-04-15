from django import forms

class NewCollectionForm(forms.Form):
    repo = forms.CharField(max_length=100)
    org = forms.CharField(max_length=100)
    cid = forms.CharField(max_length=100)

class UpdateForm(forms.Form):
    xml = forms.CharField(widget=forms.Textarea)
