from django.http import HttpResponse
from django.shortcuts import render, redirect

from webapp.forms import AnalysisForm, LoginForm, SignupForm

import subprocess

import json
import os
from django.conf import settings

from .models import User, Package, Analyses
from .forms import AnalysisForm, LoginForm, SignupForm
from django.contrib.auth import authenticate, login


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
        with open(file_path, 'r') as f: #ανοίγει αρχείο
            fulldata = json.load(f) #διαβάζει το json και το αποθηκεύει σε μεταβλητή
            bridges = fulldata.get('bridges', []) #παίρνει τη λίστα των bridges από το json, αν δεν υπάρχει επιστρέφει κενή λίστα
            objects_examined = fulldata.get('objects_examined', 0) 
            callable_objects = fulldata.get('callable_objects', 0) 
            foreign_callable_objects = fulldata.get('foreign_callable_objects', 0) 
            duration_sec = fulldata.get('duration_sec', 0) 
            count = fulldata.get('count', 0)
            modules = fulldata.get('modules', []) 
            jump_libs = fulldata.get('jump_libs', []) 
    except FileNotFoundError:
        bridges = None
        objects_examined = 0
        callable_objects = 0
        foreign_callable_objects = 0
        duration_sec = 0
        count = 0
        modules = []
        jump_libs = []

    return render(request, 'results_gasket.html', {
        'package_name': package_name,
        'bridges': bridges,
        'objects_examined': objects_examined,
        'callable_objects': callable_objects,
        'foreign_callable_objects': foreign_callable_objects,
        'duration_sec': duration_sec,
        'count': count,
        'modules': modules,
        'jump_libs': jump_libs
    })


def signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            # Δημιουργία νέου χρήστη με τα δεδομένα από τη φόρμα
            new_user = User.objects.create(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password']
            )
            #αποθηκεύουμε id στο session 
            request.session['user_id'] = new_user.id
            return redirect('workspace')
    else:
        form = SignupForm()  # Επαναφορά της φόρμας σε περίπτωση μη έγκυρων δεδομένων
    return render(request, 'signup.html', {'form': form})

def login_view(request):
    error_message = None  # Αρχικοποίηση του μηνύματος λάθους
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']           
        try:
            user = User.objects.get(username=username, password=password)
            request.session['user_id'] = user.id
            return redirect('workspace')
        except User.DoesNotExist:
            error_message = "Invalid username or password."
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form, 'error_message': error_message})


def workspace(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login') # Αν δεν είναι συνδεδεμένος, διώξε τον
        
    current_user = User.objects.get(id=user_id)
    return render(request, 'workspace.html', {'user': current_user})


def myacc(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login') # Αν δεν είναι συνδεδεμένος παει στο login
        
    current_user = User.objects.get(id=user_id)
    return render(request, 'myaccount.html', {'user': current_user})

def logout_view(request):
    if 'user_id' in request.session:
        del request.session['user_id']
    return redirect('homepage')

def analyses(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login') # Αν δεν είναι συνδεδεμένος παει στο login
        
    current_user = User.objects.get(id=user_id)
    user_analyses = current_user.user_analyses.all()  # Παίρνουμε όλες τις αναλύσεις του χρήστη
    return render(request, 'analyses.html', {'analyses': user_analyses})