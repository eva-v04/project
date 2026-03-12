from django.http import HttpResponse
from django.shortcuts import render, redirect

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
            subprocess.run(["./analyze_jelly.sh",package])

            return redirect('results', package_name = package)
            
    return render(request, 'callgraph.html', {'form': form})

def results(request, package_name):
    #url αρχείου που δημιούργησε το jelly
    graph_url = f"/static/analysis_{package_name}/{package_name}.html"
    return render(request, 'results.html', {
        'package_name' : package_name,
        'graph_url': graph_url
        })

def gasket(request):
    return render(request, 'gasket.html')