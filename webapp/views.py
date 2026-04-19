from django.http import HttpResponse
from django.shortcuts import render, redirect

from webapp.forms import AnalysisForm, LoginForm, SignupForm

import subprocess

import json
import os
from django.conf import settings

from .models import User, Package, Analyses, Notification
from .forms import AnalysisForm, LoginForm, SignupForm
from django.contrib.auth import authenticate, login

from .tasks import run_gasket_analysis, run_jelly_analysis
from django.tasks import task

import json
from django.http import JsonResponse

from .statistics import generate_full_stats

def homepage(request):
    return render(request, 'homepage.html')


def callgraph(request):
    form = AnalysisForm(request.POST)            
    user_id = request.session.get('user_id')
    current_user = User.objects.get(id=user_id) if user_id else {'username': 'Guest'}
    return render(request, 'callgraph.html', {'form': form, 'user': current_user})


def start_jelly_ajax(request):
    if request.method == 'POST':
        package = request.POST.get('package_name')
        version = request.POST.get('version', 'latest')
        
        # Λήψη τρέχοντος χρήστη
        user_id = request.session.get('user_id')
        current_user = User.objects.filter(id=user_id).first() if user_id else None

        # 1. ΕΛΕΓΧΟΣ CACHE: Ψάχνουμε αν οποιοσδήποτε χρήστης έχει ολοκληρώσει αυτή την ανάλυση
        existing_analysis = Analyses.objects.filter(
            package_name=package,
            package_version=version,
            analysis_type='jelly',
            status='completed'
        ).first()

        if existing_analysis:
            # Δημιουργούμε νέα εγγραφή για το ιστορικό του τρέχοντος χρήστη, ήδη ολοκληρωμένη
            new_analysis = Analyses.objects.create(
                package_name=package,
                package_version=version,
                user=current_user,
                analysis_type='jelly',
                status='completed',
              # task_id=existing_analysis.task_id  # Χρησιμοποιούμε το ID του υπάρχοντος task/αποτελέσματος
            )

            # Ενημέρωση session για Guests
            if not current_user:
                guest_history = request.session.get('guest_analyses', [])
                guest_history.append(new_analysis.id)
                request.session['guest_analyses'] = guest_history
                request.session.modified = True

            return JsonResponse({
                'status': 'success',
                'message': 'Call Graph found in cache!',
                'redirect': True  # Ειδοποιούμε τη JS για άμεση ανακατεύθυνση
            })

        # Δημιουργία ανάλυσης
        new_analysis = Analyses.objects.create(
            package_name=package,
            package_version=version,
            user=current_user,
            analysis_type='jelly',
            status='running'
        )

        # Session logic για guests
        if not current_user:
            guest_history = request.session.get('guest_analyses', [])
            guest_history.append(new_analysis.id)
            request.session['guest_analyses'] = guest_history
            request.session.modified = True

        # Εκκίνηση Task
        run_jelly_analysis.enqueue(package, version, analysis_id=new_analysis.id)

        return JsonResponse({
            'status': 'success',
            'analysis_id': new_analysis.id
        })
    return JsonResponse({'status': 'error'}, status=400)


def results(request, analysis_id):
    #url αρχείου που δημιούργησε το jelly
    analysis = Analyses.objects.get(id=analysis_id)

    if not analysis:
        return HttpResponse("Analysis not found.", status=404)

    package_name = analysis.package_name
    version = analysis.package_version

    graph_url = f"/static/analysis_{package_name}_{version}/{package_name}.html"
    
    context = {
        'package_name': package_name,
        'package_version': version,
        'graph_url': graph_url,
        'date': analysis.date,
        'analysis_id': analysis.id
    }
    return render(request, 'results.html', context)


def gasket(request):
    form = AnalysisForm()

    if request.method == 'POST':
        form = AnalysisForm(request.POST) 
        user_id = request.session.get('user_id')

    user_id = request.session.get('user_id')
    current_user = User.objects.get(id=user_id) if user_id else {'username': 'Guest'}
    
    return render(request, 'gasket.html', {
        'form': form,
        'user': current_user 
    })


def start_gasket_ajax(request):
    if request.method == 'POST':
        package = request.POST.get('package_name')
        version = request.POST.get('version', 'latest')
        
        # Λήψη τρέχοντος χρήστη από το session
        user_id = request.session.get('user_id')
        current_user = User.objects.filter(id=user_id).first() if user_id else None

        #Αναζήτηση αν υπάρχει ήδη ολοκληρωμένη ανάλυση (από οποιονδήποτε)
        existing_analysis = Analyses.objects.filter(
            package_name=package,
            package_version=version,
            analysis_type='gasket',
            status='completed'
        ).first()

        if existing_analysis:
            # Δημιουργούμε νέα εγγραφή για τον τρέχοντα χρήστη, αλλά με status 'completed'
            new_analysis = Analyses.objects.create(
                package_name=package,
                package_version=version,
                user=current_user,
                analysis_type='gasket',
                status='completed', # Άμεση ολοκλήρωση
               # task_id=existing_analysis.task_id # Χρήση του υπάρχοντος αποτελέσματος
            )

            # Αν είναι Guest, αποθηκεύουμε το ID στο session του
            if not current_user:
                guest_history = request.session.get('guest_analyses', [])
                guest_history.append(new_analysis.id)
                request.session['guest_analyses'] = guest_history
                request.session.modified = True

            return JsonResponse({
                'status': 'success',
                'message': 'Results found in cache!',
                'redirect': True  # Η JavaScript θα ξέρει να κάνει άμεσο redirect
            })

        # Δημιουργία ανάλυσης
        new_analysis = Analyses.objects.create(
            package_name=package,
            package_version=version,
            user=current_user,
            analysis_type='gasket',
            status='running'
        )

        # Session logic για guests
        if not current_user:
            guest_history = request.session.get('guest_analyses', [])
            guest_history.append(new_analysis.id)
            request.session['guest_analyses'] = guest_history
            request.session.modified = True

        # Εκκίνηση Task
        run_gasket_analysis.enqueue(package, version, analysis_id=new_analysis.id)

        return JsonResponse({
            'status': 'success',
            'message': 'Analysis started!',
            'analysis_id': new_analysis.id
        })
    return JsonResponse({'status': 'error'}, status=400)

    
def gasket_results(request, analysis_id):
    analysis = Analyses.objects.get(id=analysis_id)
    if not analysis:
        return HttpResponse("Analysis not found.", status=404)

    package_name = analysis.package_name
    package_version = analysis.package_version

    file_path = os.path.join(
        settings.BASE_DIR, 
        'static', 
        f'gasket_analysis_{package_name}_{package_version}', 
        f'bridges_{package_name}.json')
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
    if user_id:
        # Αν είναι συνδεδεμένος, παίρνουμε τα στοιχεία του
        current_user = User.objects.get(id=user_id)
    else:
        current_user = {'username': 'Guest'}

    return render(request, 'workspace.html', {'user': current_user})


def myacc(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return render(request, 'myaccount.html', {'user': None})        
    current_user = User.objects.get(id=user_id)
    return render(request, 'myaccount.html', {'user': current_user})


def logout_view(request):
    if 'user_id' in request.session:
        del request.session['user_id']
    return redirect('homepage')


def analyses(request):
    analyses = []
    # Παίρνουμε το ID του χρήστη από το session
    user_id = request.session.get('user_id')
    
    if user_id:
        # Φιλτράρουμε τις αναλύσεις ώστε να ανήκουν ΜΟΝΟ στον χρήστη
        # Το .order_by('-created_at') τις βάζει από την πιο πρόσφατη στην πιο παλιά
        current_user = User.objects.get(id=user_id)
        analyses = Analyses.objects.filter(user_id=user_id).order_by('-date')
    else:
        # Αν είναι guest, δείξε μόνο αυτές που έκανε σε αυτό το session
        current_user = {'username': 'Guest'}
        guest_ids = request.session.get('guest_analyses', [])
        analyses = Analyses.objects.filter(id__in=guest_ids).order_by('-date')

    return render(request, 'analyses.html', {'analyses': analyses, 'user': current_user})


def analysis_detail(request, analysis_id):
    # Παίρνουμε τη συγκεκριμένη ανάλυση από τη βάση
    analysis = Analyses.objects.get(id=analysis_id)
    
    # Αν είναι Gasket, πήγαινε στα αποτελέσματα του Gasket
    if analysis.analysis_type == 'gasket':
        return redirect('gasket_results', analysis_id=analysis.id)

    if analysis.analysis_type == 'jelly':
        return redirect('results', analysis_id=analysis.id)   
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



def check_notifications(request):
    user_id = request.session.get('user_id')

    if user_id:
        new_notifications = Notification.objects.filter(user_id=user_id, is_read=False)
    else:
        guest_analysis_ids = request.session.get('guest_analyses', [])
        
        # Αν η λίστα είναι άδεια επιστρέφουμε κενό
        if not guest_analysis_ids:
            return JsonResponse({'notifications': []})

        new_notifications = Notification.objects.filter(
            analysis_id__in=guest_analysis_ids,
            user__isnull=True, 
            is_read=False
        )

    data = []
    for n in new_notifications:
        data.append({
            'id': n.id,
            'title': n.title,
            'message': n.message, # πχ Η ανάλυση sqlite3 5.1.7 είναι έτοιμη
        })
        # διαβασμένες για να μην ξαναβγεί το pop-up
        n.is_read = True 
        n.save()

    return JsonResponse({'notifications': data})


def notifications(request):
    user_id = request.session.get('user_id')

    if user_id:
        current_user = User.objects.get(id=user_id)
        #notifications = Notification.objects.filter(user=current_user).order_by('-created_at')
        user_notifications = Notification.objects.filter(user_id=user_id).order_by('-created_at')
    else:
        guest_analysis_ids = request.session.get('guest_analyses', [])
        user_notifications = Notification.objects.filter(
            analysis_id__in=guest_analysis_ids,
        ).order_by('-created_at')

    # Μαρκάρουμε ως διαβασμένες
    user_notifications.filter(is_read=False).update(is_read=True)

    return render(request, 'notifications.html', {
        'notifications': user_notifications,
        'user': current_user if user_id else {'username': 'Guest'}
    })


def download_results(request, analysis_id):
    analysis = Analyses.objects.get(id=analysis_id)
    if not analysis:
        return HttpResponse("Analysis not found.", status=404)

    package_name = analysis.package_name
    version = analysis.package_version

    file_path = os.path.join(
        settings.BASE_DIR, 
        'static', 
        f'analysis_{package_name}_{version}', 
        f'{package_name}.html')
    
    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='text/html')
            response['Content-Disposition'] = f'attachment; filename="{package_name}_callgraph.html"'
            return response
    else:
        return HttpResponse("File not found.", status=404)


def statistics(request, analysis_id):
    analysis = Analyses.objects.get(id=analysis_id)
    pkg = analysis.package_name
    ver = analysis.package_version

    stats_data = generate_full_stats(pkg, ver)
    
    if stats_data is None:
        stats_data = {}

    return render(request, 'statistics.html', {
        'stats': stats_data,
        'package_name': pkg,
        'analysis_id': analysis_id
    })