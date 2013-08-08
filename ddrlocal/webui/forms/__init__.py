from django import forms

class LoginForm(forms.Form):
    username = forms.CharField(max_length=100)
    password = forms.CharField(widget=forms.PasswordInput)
    next = forms.CharField(max_length=255, required=False, widget=forms.HiddenInput)

class TaskDismissForm(forms.Form):
    next = forms.CharField(max_length=255, required=False, widget=forms.HiddenInput)
