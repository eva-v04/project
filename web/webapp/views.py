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

from .tasks import run_gasket_analysis, run_jelly_analysis, run_cross_language_analysis
from django.tasks import task

import json
from django.http import JsonResponse

from .statistics import generate_full_stats
from .statistics import generate_full_stats, get_matplotlib_graph, get_matplotlib_bar_graph

from django.utils import timezone

def homepage(request):
    return render(request, 'homepage.html')


def callgraph(request):
    form = AnalysisForm(request.POST)            
    user_id = request.session.get('user_id')
    current_user = User.objects.get(id=user_id) if user_id else {'username': 'Guest'}
    return render(request, 'callgraph.html', {'form': form, 'user': current_user})


def start_jelly_ajax(request):
    if request.method == 'POST':
        package = request.POST.get('package_name', '').strip()
        version = request.POST.get('version', '').strip() or 'latest'
        
        user_id = request.session.get('user_id')
        current_user = User.objects.filter(id=user_id).first() if user_id else None

        existing_analysis = Analyses.objects.filter(
            package_name=package,
            package_version=version,
            analysis_type='jelly',
            status='completed'
        ).first()

        if existing_analysis:
            new_analysis = Analyses.objects.create(
                package_name=package,
                package_version=version,
                user=current_user,
                analysis_type='jelly',
                status='completed',
                progress=100,
                current_step='Completed (from cache)'
            )
            if not current_user:
                if not request.session.session_key:
                    request.session.create()
                guest_history = request.session.get('guest_analyses', [])
                guest_history.append(new_analysis.id)
                request.session['guest_analyses'] = guest_history
                request.session.modified = True
                request.session.save()

            return JsonResponse({'status': 'success', 'message': 'Found in cache!', 'redirect': True})

        new_analysis = Analyses.objects.create(
            package_name=package,
            package_version=version,
            user=current_user,
            analysis_type='jelly',
            status='running',
            progress=5,
            current_step='Starting Jelly Analysis...'
        )

        if not current_user:
            if not request.session.session_key:
                request.session.create()
            guest_history = request.session.get('guest_analyses', [])
            guest_history.append(new_analysis.id)
            request.session['guest_analyses'] = guest_history
            request.session.modified = True
            request.session.save()

        run_jelly_analysis.enqueue(package, version, analysis_id=new_analysis.id)
        return JsonResponse({'status': 'success', 'analysis_id': new_analysis.id})


def results(request, analysis_id):
    analysis = Analyses.objects.get(id=analysis_id)
    if not analysis:
        return HttpResponse("Analysis not found.", status=404)

    package_name = analysis.package_name
    version = analysis.package_version

    graph_url = f"/static/analysis_{package_name}_{version}/{package_name}.html"
    json_url = f"/static/analysis_{package_name}_{version}/{package_name}.json"  #Jelly JSON path
    
    context = {
        'package_name': package_name,
        'package_version': version,
        'graph_url': graph_url,
        'json_url': json_url,
        'date': analysis.date,
        'analysis_id': analysis.id,
        'analysis_type': analysis.analysis_type
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
        package = request.POST.get('package_name', '').strip()
        version = request.POST.get('version', '').strip() or 'latest'
        
        user_id = request.session.get('user_id')
        current_user = User.objects.filter(id=user_id).first() if user_id else None

        existing_analysis = Analyses.objects.filter(
            package_name=package,
            package_version=version,
            analysis_type='gasket',
            status='completed'
        ).first()

        if existing_analysis:
            new_analysis = Analyses.objects.create(
                package_name=package,
                package_version=version,
                user=current_user,
                analysis_type='gasket',
                status='completed',
                progress=100,
                current_step='Completed (from cache)'
            )
            if not current_user:
                if not request.session.session_key:
                    request.session.create()
                guest_history = request.session.get('guest_analyses', [])
                guest_history.append(new_analysis.id)
                request.session['guest_analyses'] = guest_history
                request.session.modified = True
                request.session.save()

            return JsonResponse({'status': 'success', 'message': 'Found in cache!', 'redirect': True})

        new_analysis = Analyses.objects.create(
            package_name=package,
            package_version=version,
            user=current_user,
            analysis_type='gasket',
            status='running',
            progress=5,
            current_step='Starting Gasket Analysis...'
        )

        if not current_user:
            if not request.session.session_key:
                request.session.create()
            guest_history = request.session.get('guest_analyses', [])
            guest_history.append(new_analysis.id)
            request.session['guest_analyses'] = guest_history
            request.session.modified = True
            request.session.save()

        run_gasket_analysis.enqueue(package, version, analysis_id=new_analysis.id)
        return JsonResponse({'status': 'success', 'analysis_id': new_analysis.id})

    
def gasket_results(request, analysis_id):
    #  ανάκτηση της ανάλυσης
    analysis = Analyses.objects.filter(id=analysis_id).first()
    if not analysis:
        return HttpResponse("Analysis not found.", status=404)

    package_name = analysis.package_name
    package_version = analysis.package_version

    file_path = os.path.join(
        settings.BASE_DIR, 
        'static', 
        f'gasket_analysis_{package_name}_{package_version}', 
        f'bridges_{package_name}.json'
    )
    
    # Διαδρομή static για το Export JSON κουμπί
    json_url = f"/static/gasket_analysis_{package_name}_{package_version}/bridges_{package_name}.json"

    try:
        with open(file_path, 'r') as f:
            fulldata = json.load(f)
            bridges = fulldata.get('bridges', [])
            
            for bridge in bridges:
                lib = bridge.get('library', 'Unknown')
                bridge['display_lib'] = lib.split('/')[-1]

            objects_examined = fulldata.get('objects_examined', 0)
            callable_objects = fulldata.get('callable_objects', 0)
            foreign_callable_objects = fulldata.get('foreign_callable_objects', 0)
            duration_sec = fulldata.get('duration_sec', 0)
            count = fulldata.get('count', 0)
            modules = fulldata.get('modules', [])
            jump_libs = fulldata.get('jump_libs', [])
    except (FileNotFoundError, json.JSONDecodeError):
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
        'jump_libs': jump_libs,
        'json_url': json_url,
        'analysis_id': analysis.id,
        'date': analysis.date
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
    version = analysis.package_version

    stats_data = generate_full_stats(pkg, version)

    if stats_data is None:
        stats_data = {}

    stats_f = stats_data.get('function_stats', {})
    stats_fi = stats_data.get('file_stats', {})
    stats_p = stats_data.get('package_stats', {})

    context = {
        'stats': stats_data,
        'package_name': pkg,
        'package_version': version,
        'analysis_id': analysis_id,
        
        # Pie Charts
        'chart_functions': get_matplotlib_graph(stats_f.get('reachable_functions', 0), stats_f.get('total_functions', 0)),
        'chart_files': get_matplotlib_graph(stats_fi.get('reachable_files', 0), stats_fi.get('total_files', 0)),
        'chart_packages': get_matplotlib_graph(stats_p.get('reachable_packages', 0), stats_p.get('total_packages', 0)),
        
        # Bar Charts (Αν έχεις υλοποιήσει τη συνάρτηση get_matplotlib_bar_graph)
        'bar_functions': get_matplotlib_bar_graph(stats_f.get('reachable_functions', 0), stats_f.get('total_functions', 0)),
        'bar_files': get_matplotlib_bar_graph(stats_fi.get('reachable_files', 0), stats_fi.get('total_files', 0)),
        'bar_packages': get_matplotlib_bar_graph(stats_p.get('reachable_packages', 0), stats_p.get('total_packages', 0)),
    }
    
    return render(request, 'statistics.html', context)


def cross_language(request):
    form = AnalysisForm()
    user_id = request.session.get('user_id')
    current_user = User.objects.get(id=user_id) if user_id else {'username': 'Guest'}
    
    return render(request, 'cross_language.html', {
        'form': form,
        'user': current_user
    })


def start_cross_language_ajax(request):
    if request.method == 'POST':
        package = request.POST.get('package_name', '').strip()
        version = request.POST.get('version', '').strip() or 'latest'
        
        if not package:
            return JsonResponse({'status': 'error', 'message': 'Package name is required.'}, status=400)

        # Λήψη τρέχοντος χρήστη από το session
        user_id = request.session.get('user_id')
        current_user = User.objects.filter(id=user_id).first() if user_id else None

        # ΕΛΕΓΧΟΣ CACHE
        existing_analysis = Analyses.objects.filter(
            package_name=package,
            package_version=version,
            analysis_type='cross_language',
            status='completed'
        ).first()

        if existing_analysis:
            new_analysis = Analyses.objects.create(
                package_name=package,
                package_version=version,
                user=current_user,
                analysis_type='cross_language',
                status='completed',
                progress=100,
                current_step='Completed (from cache)'
            )

            # Αποθήκευση στο Session για Guests
            if not current_user:
                if not request.session.session_key:
                    request.session.create()
                guest_history = request.session.get('guest_analyses', [])
                guest_history.append(new_analysis.id)
                request.session['guest_analyses'] = guest_history
                request.session.modified = True
                request.session.save()

            return JsonResponse({
                'status': 'success',
                'message': 'Cross-Language analysis found in cache!',
                'redirect': True
            })

        #  Δημιουργία νέας ανάλυσης στη βάση δεδομένων
        new_analysis = Analyses.objects.create(
            package_name=package,
            package_version=version,
            user=current_user,
            analysis_type='cross_language',
            status='running',
            progress=5,
            current_step='Starting Cross-Language Analysis...'
        )

        # Άμεση κατοχύρωση Session για Guests
        if not current_user:
            if not request.session.session_key:
                request.session.create()
            guest_history = request.session.get('guest_analyses', [])
            guest_history.append(new_analysis.id)
            request.session['guest_analyses'] = guest_history
            request.session.modified = True
            request.session.save()  # Εξασφαλίζει άμεση εγγραφή του cookie

        
        run_cross_language_analysis.enqueue(package, version, analysis_id=new_analysis.id)

        return JsonResponse({
            'status': 'success',
            'message': 'Cross-Language Analysis started!',
            'analysis_id': new_analysis.id
        })
        
    return JsonResponse({'status': 'error'}, status=400)



def cross_language_results(request, analysis_id):
    analysis = Analyses.objects.get(id=analysis_id)
    if not analysis:
        return HttpResponse("Analysis not found.", status=404)

    package_name = analysis.package_name
    version = analysis.package_version

    # Σύνδεση με το τελικό ενοποιημένο HTML & JSON
    graph_url = f"/static/cross_analysis_{package_name}_{version}/{package_name}.html"
    json_url = f"/static/cross_analysis_{package_name}_{version}/{package_name}.json"  # Cross-Language JSON path
    
    context = {
        'package_name': package_name,
        'package_version': version,
        'graph_url': graph_url,
        'json_url': json_url,
        'date': analysis.date,
        'analysis_id': analysis.id,
        'analysis_type': analysis.analysis_type
    }
    return render(request, 'results.html', context)


def analysis_detail(request, analysis_id):
    analysis = Analyses.objects.get(id=analysis_id)
    
    if analysis.analysis_type == 'gasket':
        return redirect('gasket_results', analysis_id=analysis.id)

    if analysis.analysis_type == 'jelly':
        return redirect('results', analysis_id=analysis.id)

    if analysis.analysis_type == 'cross_language':
        return redirect('cross_language_results', analysis_id=analysis.id)

    return redirect('analyses')



def get_active_analyses_status(request):
    user_id = request.session.get('user_id')
    guest_ids = request.session.get('guest_analyses', [])

    if user_id:
        running_analyses = Analyses.objects.filter(user_id=user_id, status='running')
    elif guest_ids:
        running_analyses = Analyses.objects.filter(id__in=guest_ids, status='running')
    else:
        recent_cutoff = timezone.now() - timedelta(minutes=10)
        running_analyses = Analyses.objects.filter(user__isnull=True, status='running', date__gte=recent_cutoff)

    data = []
    for a in running_analyses:
        data.append({
            'id': a.id,
            'package_name': a.package_name,
            'version': a.package_version,
            'analysis_type': a.analysis_type.upper(),
            'progress': a.progress,
            'current_step': a.current_step
        })

    return JsonResponse({'active_analyses': data})