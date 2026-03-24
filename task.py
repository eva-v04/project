from django.tasks import task
import subprocess

@task
def run_gasket_analysis(package_name):
    # Εκτέλεση του script
    subprocess.run(["./analyze_gasket.sh", package_name])
    
    # Ενημέρωση της βάσης δεδομένων
    from .models import Analyses
    analysis = Analyses.objects.filter(package_name=package_name, status='running').last()
    if analysis:
        analysis.status = 'completed'
        analysis.save()
        
    return "Analysis Complete"