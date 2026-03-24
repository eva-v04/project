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

from .tasks import run_gasket_analysis, run_jelly_analysis
from django.tasks import task

import json
from django.http import JsonResponse

def homepage(request):
    return render(request, 'homepage.html')


def callgraph(request):
    form = AnalysisForm()

    if request.method == 'POST':
        form = AnalysisForm(request.POST)
        if form.is_valid():
            package = form.cleaned_data['package_name']
            package_version = request.POST.get('package_version', 'latest')  # Παίρνουμε την έκδοση από το POST, αν δεν υπάρχει χρησιμοποιούμε "latest"

            #subprocess.run(["./analyze_jelly.sh",package])

            user_id = request.session.get('user_id')
            user = User.objects.get(id=user_id) if user_id else None

            if user is None:
                error_message = "You must be logged in to run the analysis."
                return render(request, 'callgraph.html', {'form': form, 'error_message': error_message})

            task_result = run_jelly_analysis.enqueue(package, package_version)

            new_analysis = Analyses.objects.create(
                package_name=package,
                package_version=package_version,
                user=user,
                analysis_type='jelly',
                status='running',
                task_id=task_result.id
            )  # Αποθήκευση της ανάλυσης στη βάση δεδομένων

            #return redirect('results', package_name=package, package_version=package_version)
            return redirect('results', package_name=package)
            
    return render(request, 'callgraph.html', {'form': form})


def results(request, package_name):
    #url αρχείου που δημιούργησε το jelly
    graph_url = f"/static/analysis_{package_name}/{package_name}.html"
    return render(request, 'results.html', {
        'package_name' : package_name,
        'graph_url': graph_url
        })


def gasket(request):
    form = AnalysisForm()

    if request.method == 'POST':
        form = AnalysisForm(request.POST) 
        
        if form.is_valid():
            package = form.cleaned_data['package_name']
            package_version = request.POST.get('version', 'latest')  # Παίρνουμε την έκδοση από το POST, αν δεν υπάρχει χρησιμοποιούμε "latest"

            user_id = request.session.get('user_id')
            if user_id:
                user = User.objects.get(id=user_id)
            else:
                user = None  # Αν δεν υπάρχει συνδεδεμένος χρήστης, θέτουμε το user σε None
                error_message = "You must be logged in to run the Gasket analysis."
                return render(request, 'gasket.html', {'form': form, 'error_message': error_message})

            # Εκτέλεση του Docker script για το Gasket
            #subprocess.run(["./analyze_gasket.sh", package])

            new_analysis = Analyses.objects.create(
                package_name=package,
                package_version=package_version,
                user=user,
                analysis_type='gasket',
                status='running',
                task_id=''  # Θα ενημερωθεί μετά την εκκίνηση του task
            )
            task_result = run_gasket_analysis.enqueue(package, package_version)  # Εδώ δεν έχουμε ακόμα το task_id, θα το περάσουμε μετά
            
            new_analysis.task_id = task_result.id
            new_analysis.save()

            task_result = run_gasket_analysis.enqueue(package, package_version, task_id=task_result.id)

            #return redirect('results_gasket', package_name=package, package_version=package_version)
            return redirect('gasket_results', package_name=package, package_version=package_version)
            
    return render(request, 'gasket.html', {'form': form})


def gasket_results(request, package_name, package_version):
    file_path = os.path.join(settings.BASE_DIR, 'static', f'gasket_analysis_{package_name}', f'bridges_{package_name}_{package_version}.json')    
    try:
        with open(file_path, 'r') as f: #ανοίγει αρχείο
            fulldata = json.load(f) #διαβάζει το json και το αποθηκεύει σε μεταβλητή
            bridges = fulldata.get('bridges', []) #παίρνει τη λίστα των bridges από το json, αν δεν υπάρχει επιστρέφει κενή λίστα
            #library είναι το πλήρες path του αρχείου, display_lib είναι μόνο το όνομα του αρχείου για εμφάνιση στο template
            for bridge in bridges:
                lib = bridge.get('library', 'Unknown') 
                # Κρατάμε μόνο το όνομα του αρχείου (π.χ. node_sqlite3.node)
                bridge['display_lib'] = lib.split('/')[-1]
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
        'package_version': package_version,
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
    # Παίρνουμε το ID του χρήστη από το session
    user_id = request.session.get('user_id')
    
    if user_id:
        # Φιλτράρουμε τις αναλύσεις ώστε να ανήκουν ΜΟΝΟ στον χρήστη
        # Το .order_by('-created_at') τις βάζει από την πιο πρόσφατη στην πιο παλιά
        analyses = Analyses.objects.filter(user_id=user_id).order_by('-date')
    else:
        analyses = []

    return render(request, 'analyses.html', {'analyses': analyses})

def analysis_detail(request, analysis_id):
    # Παίρνουμε τη συγκεκριμένη ανάλυση από τη βάση
    analysis = Analyses.objects.get(id=analysis_id)
    
    # Αν είναι Gasket, πήγαινε στα αποτελέσματα του Gasket
    if analysis.analysis_type == 'gasket':
        return redirect('gasket_results', package_name=analysis.package_name, package_version=analysis.package_version)

    if analysis.analysis_type == 'jelly':
        return redirect('results', package_name=analysis.package_name)    
    return redirect('analyses')

def get_package_versions(request):
    package_name = request.GET.get('package_name')
    if not package_name:
        return JsonResponse({'versions': []})

    try:
        # Εκτελούμε την εντολή npm show για να πάρουμε τις εκδόσεις σε JSON format
        result = subprocess.check_output(
            ["npm", "show", package_name, "versions", "--json"],
            stderr=subprocess.STDOUT,
            text=True
        )
        versions = json.loads(result)

        # Αν το npm επιστρέψει μόνο μία έκδοση (string), τη μετατρέπουμε σε λίστα
        if isinstance(versions, str):
            versions = [versions]

        # Επιστρέφουμε τις εκδόσεις αντίστροφα (οι πιο πρόσφατες πρώτες)
        return JsonResponse({'versions': versions[::-1]})
    
    except Exception as e:
        # Αν υπάρξει σφάλμα (π.χ. δεν υπάρχει το πακέτο), επιστρέφουμε κενή λίστα
        print(f"Error fetching versions: {e}")
        return JsonResponse({'versions': []})