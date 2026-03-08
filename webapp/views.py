from django.http import HttpResponse
from django.shortcuts import render

from webapp.forms import AnalysisForm

import subprocess

def homepage(request):
    return render(request, 'homepage.html')

def callgraph(request):
    form = AnalysisForm()

    if request.method == 'POST':
        form = AnalysisForm(request.POST)
        if form.is_valid():
            package = form.cleaned_data['package_name']
            subprocess.run(["./npmname.sh",package])
            
    return render(request, 'callgraph.html', {'form': form})
