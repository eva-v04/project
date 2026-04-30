from django import forms
from .models import Analyses, Package

class AnalysisForm(forms.ModelForm):
    package_name = forms.CharField(max_length=150, required=True)

    class Meta:
        model = Analyses
        fields = ['package_name']

class SignupForm(forms.Form):
    username = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)

class LoginForm(forms.Form):
    username = forms.CharField(max_length=150, required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)