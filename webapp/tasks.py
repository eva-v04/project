from django.tasks import task
import subprocess

@task
def run_gasket_analysis(package_name, package_version=None):
    # Εκτέλεση του script
    if package_version:
        subprocess.run(["./analyze_gasket.sh", package_name, package_version])
    else:
        subprocess.run(["./analyze_gasket.sh", package_name])
    
    # Ενημέρωση της βάσης δεδομένων
    from .models import Analyses
    analysis = Analyses.objects.filter(
        package_name=package_name, 
        status='running').last()
        #προσθέτω version
    if analysis:
        analysis.status = 'completed' #Γιατι δεν αλλάζει το status;;;;
        analysis.save()
    
    #user = User.objects.get(id=user_id)
    #Notification.objects.create(
     #   user=user,
      #  message=f"Analysis for {package_name} completed!",
       # link=f"/gasket_results/{package_name}/"
    #)

    return "Analysis Complete"

@task
def run_jelly_analysis(package_name, package_version=None):
    # Εκτέλεση του script για Jelly
    if package_version:
        subprocess.run(["./analyze_jelly.sh", package_name, package_version])
    else:
        subprocess.run(["./analyze_jelly.sh", package_name])
    
    # Ενημέρωση της βάσης δεδομένων
    from .models import Analyses
    analysis = Analyses.objects.filter(
        package_name=package_name, 
        status='running', 
        analysis_type='jelly').last()
        #προσθέτω version
    if analysis:
        analysis.status = 'completed'
        analysis.save()
        
    #user = User.objects.get(id=user_id)
    #Notification.objects.create(
     #   user=user,
      #  message=f"Analysis for {package_name} completed!",
       # link=f"/jelly_results/{package_name}/"
    #)
    return "Jelly Analysis Complete"