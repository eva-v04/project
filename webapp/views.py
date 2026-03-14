from django.http import HttpResponse
from django.shortcuts import render, redirect

from webapp.forms import AnalysisForm

import subprocess

import json
import os
from django.conf import settings

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
    form = AnalysisForm() # Χρησιμοποιούμε την ίδια φόρμα για το package name

    if request.method == 'POST':
        form = AnalysisForm(request.POST)
        if form.is_valid():
            package = form.cleaned_data['package_name']
            # Εκτέλεση του Docker script για το Gasket
            subprocess.run(["./analyze_gasket.sh", package])
            
            # Ανακατεύθυνση στη σελίδα των αποτελεσμάτων του Gasket
            return redirect('gasket_results', package_name=package)
            
    return render(request, 'gasket.html', {'form': form})

def gasket_results(request, package_name):
    file_path = os.path.join(settings.BASE_DIR, 'static', f'gasket_analysis_{package_name}', f'bridges_{package_name}.json')    
    try:
        with open(file_path, 'r') as f:
            fulldata = json.load(f)
            data = fulldata.get('bridges', [])
    except FileNotFoundError:
        data = None

    return render(request, 'results_gasket.html', {
        'package_name': package_name,
        'bridges': data
    })