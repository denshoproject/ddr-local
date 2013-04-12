from django import forms

class LoginForm(forms.Form):
    git_name = forms.CharField(max_length=100)
    git_mail = forms.EmailField()
    username = forms.CharField(max_length=100)
    password = forms.CharField(widget=forms.PasswordInput)
