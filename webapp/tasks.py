from django.tasks import task
#import dramatiq
from .models import Analyses, User, Notification
import subprocess

#@dramatiq.actor
@task
def run_gasket_analysis(package_name, package_version=None, analysis_id=None):
    
    # Εκτέλεση του script
    if package_version:
        subprocess.run(["./analyze_gasket.sh", package_name, package_version])
    else:
        subprocess.run(["./analyze_gasket.sh", package_name])
        
    analysis = Analyses.objects.filter(id=analysis_id).first()

    if analysis:
        analysis.status = 'completed'
        analysis.save()

        # Δημιουργία ειδοποίησης για τον χρήστη
        if analysis.user:
            Notification.objects.create(
                user=analysis.user,
                analysis=analysis,
                message=f"Your gasket analysis for {package_name} is complete!",
                title="Gasket Analysis Complete",
                link=f"/analysis/{analysis.id}/"  
            )
        else:
            # Για τους guest χρήστες
            Notification.objects.create(
                user=None,
                analysis=analysis,
                message=f"Your gasket analysis for {package_name} is complete!",
                title="Gasket Analysis Complete",
                link=f"/analysis/{analysis.id}/"  
            )
        return f"Analysis for {package_name} completed."
    else:
        return "Analysis record not found."


@task
def run_jelly_analysis(package_name, package_version=None, analysis_id=None):
    # Εκτέλεση του script για Jelly
    if package_version:
        subprocess.run(["./analyze_jelly.sh", package_name, package_version])
    else:
        subprocess.run(["./analyze_jelly.sh", package_name])
    
    analysis = Analyses.objects.filter(id=analysis_id).first()

    if analysis:
        analysis.status = 'completed'
        analysis.save()

        # Δημιουργία ειδοποίησης για τον χρήστη
        if analysis.user:
            Notification.objects.create(
                user=analysis.user,
                analysis=analysis,
                message=f"Your jelly analysis for {package_name} is complete!",
                title="Jelly Analysis Complete",
                link=f"/analysis/{analysis.id}/" 
            )
        else:
            # Για τους guest χρήστες
            Notification.objects.create(
                user=None,
                analysis=analysis,
                message=f"Your jelly analysis for {package_name} is complete!",
                title="Jelly Analysis Complete",
                link=f"/analysis/{analysis.id}/" 
            )
        return f"Analysis for {package_name} completed."
    else:
        return "Analysis record not found."
