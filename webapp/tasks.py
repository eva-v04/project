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
    
    #ψάχνουμε την ανάλυση που αντιστοιχεί στο task_id
    try:
        analysis = Analyses.objects.filter(task_id=task_id).first()
        analysis.status = 'completed'
        analysis.save()
        return f"Analysis for {package_name} completed."
    except Analyses.DoesNotExist:
        return "Analysis record not found."
    
    #user = User.objects.get(id=user_id)
    #Notification.objects.create(
     #   user=user,
      #  message=f"Analysis for {package_name} completed!",
       # link=f"/gasket_results/{package_name}/"
    #)


@task
def run_jelly_analysis(package_name, package_version=None):
    # Εκτέλεση του script για Jelly
    if package_version:
        subprocess.run(["./analyze_jelly.sh", package_name, package_version])
    else:
        subprocess.run(["./analyze_jelly.sh", package_name])
    
    # Ενημέρωση της βάσης δεδομένων
    try:
        analysis = Analyses.objects.filter(task_id=task_id).first()
        analysis.status = 'completed'
        analysis.save()
        return f"Analysis for {package_name} completed."
    except Analyses.DoesNotExist:
        return "Analysis record not found."
        
    #user = User.objects.get(id=user_id)
    #Notification.objects.create(
     #   user=user,
      #  message=f"Analysis for {package_name} completed!",
       # link=f"/jelly_results/{package_name}/"
    #)
    return "Jelly Analysis Complete"