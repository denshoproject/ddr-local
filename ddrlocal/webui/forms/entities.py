from django import forms

class NewEntityForm(forms.Form):
    eid = forms.CharField(max_length=100)

class UpdateForm(forms.Form):
    xml = forms.CharField(widget=forms.Textarea)
