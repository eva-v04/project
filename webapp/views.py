from django.http import HttpResponse
from django.shortcuts import render

from webapp.forms import AnalysisForm


def homepage(request):
    return render(request, 'homepage.html')


def callgraph(request):
    form = AnalysisForm()
    return render(request, 'callgraph.html', {'form': form})