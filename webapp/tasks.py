from django.tasks import task
import subprocess

@task
def run_gasket_analysis(package_name):
    subprocess.run(["./analyze_gasket.sh", package_name])
    return "Analysis Complete"