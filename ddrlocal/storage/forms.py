from django import forms

class MountForm(forms.Form):
    which = forms.CharField(max_length=10, required=True, initial='mount')

class UmountForm(forms.Form):
    which = forms.CharField(max_length=10, required=True, initial='umount')
