from django.tasks import task
from .models import Analyses, User, Notification
import subprocess

@task
def run_gasket_analysis(package_name, package_version=None, task_id=None):
    
    # Εκτέλεση του script
    if package_version:
        subprocess.run(["./analyze_gasket.sh", package_name, package_version])
    else:
        subprocess.run(["./analyze_gasket.sh", package_name])
        
    analysis = Analyses.objects.filter(task_id=task_id).first()

    if analysis:
        analysis.status = 'completed'
        analysis.save()

        # Δημιουργία ειδοποίησης για τον χρήστη
        if analysis.user:
            Notification.objects.create(
                user=analysis.user,
                message=f"Your analysis for {package_name} is complete!",
                link=f"/analysis/{analysis.id}/"  
            )
        return f"Analysis for {package_name} completed."
    else:
        return "Analysis record not found."


@task
def run_jelly_analysis(package_name, package_version=None, task_id=None):
    # Εκτέλεση του script για Jelly
    if package_version:
        subprocess.run(["./analyze_jelly.sh", package_name, package_version])
    else:
        subprocess.run(["./analyze_jelly.sh", package_name])
    
    analysis = Analyses.objects.filter(task_id=task_id).first()

    if analysis:
        analysis.status = 'completed'
        analysis.save()

        # Δημιουργία ειδοποίησης για τον χρήστη
        if analysis.user:
            Notification.objects.create(
                user=analysis.user,
                message=f"Your analysis for {package_name} is complete!",
                link=f"/analysis/{analysis.id}/"  # Υποθέτοντας ότι αυτή είναι η URL για τα αποτελέσματα
            )
        return f"Analysis for {package_name} completed."
    else:
        return "Analysis record not found."