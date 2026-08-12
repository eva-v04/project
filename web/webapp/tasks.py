import os
import glob
import subprocess
from django.tasks import task
from django.conf import settings
from .models import Analyses, User, Notification


@task
def run_gasket_analysis(package_name, package_version=None, analysis_id=None):
    # Εκτέλεση του script για Gasket
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

        if analysis.user:
            Notification.objects.create(
                user=analysis.user,
                analysis=analysis,
                message=f"Your jelly analysis for {package_name} is complete!",
                title="Jelly Analysis Complete",
                link=f"/analysis/{analysis.id}/" 
            )
        else:
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




@task
def run_cross_language_analysis(package_name, package_version=None, analysis_id=None):
    analysis = Analyses.objects.filter(id=analysis_id).first()
    
    if not analysis:
        return "Analysis record not found."

    try:
        version_param = package_version if (package_version and package_version.strip()) else "latest"

        # Ορισμός διαδρομών
        gasket_folder = os.path.join(
            settings.BASE_DIR, 
            'static', 
            f'gasket_analysis_{package_name}_{version_param}'
        )
        expected_bridges_file = os.path.join(gasket_folder, f'bridges_{package_name}.json')
        expected_ghidra_file = os.path.join(settings.BASE_DIR, 'static', f'ghidra_{package_name}.json')

        gasket_script = os.path.join(settings.BASE_DIR, "analyze_gasket.sh")
        cross_script = os.path.join(settings.BASE_DIR, "analyze_cross.sh")
        ghidra_script = "/home/eva/ghidra-callgraph/ghidra.sh"

        #
        if os.path.exists(expected_bridges_file) and os.path.getsize(expected_bridges_file) > 0:
            print(f" [GASKET CACHE HIT] Βρέθηκαν έτοιμα τα bridges: {expected_bridges_file}")
        else:
            print(f" [GASKET CACHE MISS] Εκτέλεση Gasket για {package_name}@{version_param}...")
            try:
                subprocess.run(
                    [gasket_script, package_name, version_param], 
                    cwd=settings.BASE_DIR, 
                    check=True
                )
            except subprocess.CalledProcessError as e:
                analysis.status = 'failed'
                analysis.save()
                
                notification_user = analysis.user if analysis.user else None
                Notification.objects.create(
                    user=notification_user,
                    analysis=analysis,
                    title="Cross-Language Analysis Failed",
                    message=f"Η ανάλυση Gasket για το πακέτο {package_name} ({version_param}) απέτυχε.",
                    link="/analyses/"
                )
                return f"Gasket execution failed: {e}"

        # -------------------------------------------------------------
        # ΝΤΟΠΙΣΜΟΣ ΚΑΤΑΛΛΗΛΟΥ .NODE ΑΡΧΕΙΟΥ (Προτίμηση x64/linux-x64)!!!!!!!!!
        # -------------------------------------------------------------
        jelly_folder = os.path.join(
            settings.BASE_DIR, 
            'static', 
            f'analysis_{package_name}_{version_param}'
        )

        all_node_files = glob.glob(f"{gasket_folder}/**/*.node", recursive=True) + \
                         glob.glob(f"{jelly_folder}/**/*.node", recursive=True) + \
                         glob.glob(f"/home/eva/node_modules/{package_name}/**/*.node", recursive=True)

        if not all_node_files:
            raise FileNotFoundError(f"Δεν βρέθηκε αρχείο .node για το πακέτο {package_name}")

        # Δίνουμε προτεραιότητα σε x64 binaries για να μην διαλέγει τυχαία armv7
        x64_nodes = [f for f in all_node_files if 'x64' in f or 'x86_64' in f or 'linux' in f]
        native_binary_path = x64_nodes[0] if x64_nodes else all_node_files[0]
        
        print(f"Native binary selected: {native_binary_path}")

        
        if os.path.exists(expected_ghidra_file) and os.path.getsize(expected_ghidra_file) > 0:
            print(f" [GHIDRA CACHE HIT] Βρέθηκε έτοιμη η ανάλυση Ghidra: {expected_ghidra_file}")
        else:
            print(f" [GHIDRA CACHE MISS] Εκτέλεση Ghidra για {package_name}...")
            subprocess.run(
                [ghidra_script, native_binary_path, package_name], 
                cwd=settings.BASE_DIR, 
                check=True
            )

        # -------------------------------------------------------------
        # 4. ΕΚΤΕΛΕΣΗ CROSS-LANGUAGE JELLY SCRIPT
        # -------------------------------------------------------------
        print(f"Εκτέλεση Cross-Language Jelly για {package_name}@{version_param}...")
        subprocess.run(
            [cross_script, package_name, version_param], 
            cwd=settings.BASE_DIR, 
            check=True
        )

        
        analysis.status = 'completed'
        analysis.save()

        notification_user = analysis.user if analysis.user else None
        Notification.objects.create(
            user=notification_user,
            analysis=analysis,
            title="Cross-Language Analysis Complete",
            message=f"Your Cross-Language analysis for {package_name} ({version_param}) is complete!",
            link=f"/analysis/{analysis.id}/"
        )

        return f"Cross-Language analysis for {package_name} completed successfully."

    except Exception as e:
        analysis.status = 'failed'
        analysis.save()
        print(f"Error running cross-language analysis for {package_name}: {e}")
        return f"Analysis failed: {str(e)}"