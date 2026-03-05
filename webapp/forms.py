from django import forms
from .models import analysis, package

class AnalysisForm(forms.ModelForm):
    package_name = forms.CharField(max_length=150, required=True)

    class Meta:
        model = analysis
        fields = ['package_name']