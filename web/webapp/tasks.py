import os
import glob
import subprocess
import json
from django.tasks import task
from django.conf import settings
from .models import Analyses, User, Notification


@task
def run_gasket_analysis(package_name, package_version=None, analysis_id=None):
    analysis = Analyses.objects.filter(id=analysis_id).first()
    version_param = package_version if (package_version and package_version.strip()) else "latest"

    if not analysis:
        return "Analysis record not found."

    try:
        # Βήμα 1: Εκκίνηση Gasket
        analysis.progress = 25
        analysis.current_step = f"Initializing Gasket environment for {package_name}@{version_param}..."
        analysis.save()

        analysis.progress = 50
        analysis.current_step = "Extracting Native C/C++ memory bridges..."
        analysis.save()

        # Εκτέλεση του script
        if package_version:
            cmd = ["./analyze_gasket.sh", package_name, package_version]
        else:
            cmd = ["./analyze_gasket.sh", package_name]

        # Τρέχουμε χωρίς check=True για να μην καταρρέει αυτόματα αν το αρχείο υπάρχει
        subprocess.run(cmd, cwd=settings.BASE_DIR)

        # Βήμα 2: Ολοκλήρωση
        analysis.progress = 100
        analysis.current_step = "Completed!"
        analysis.status = 'completed'
        analysis.save()

        Notification.objects.create(
            user=analysis.user,
            analysis=analysis,
            message=f"Your gasket analysis for {package_name} ({version_param}) is complete!",
            title="Gasket Analysis Complete",
            link=f"/results_gasket/{analysis.id}/"
        )
        return f"Analysis for {package_name} completed."

    except Exception as e:
        analysis.status = 'failed'
        analysis.progress = 0
        analysis.current_step = f"Gasket Failed: {str(e)}"
        analysis.save()

        Notification.objects.create(
            user=analysis.user,
            analysis=analysis,
            title="Gasket Analysis Failed",
            message=f"Η ανάλυση Gasket για το πακέτο {package_name} ({version_param}) απέτυχε.",
            link="/analyses/"
        )
        return f"Gasket failed: {e}"


@task
def run_jelly_analysis(package_name, package_version=None, analysis_id=None):
    analysis = Analyses.objects.filter(id=analysis_id).first()
    version_param = package_version if (package_version and package_version.strip()) else "latest"

    if not analysis:
        return "Analysis record not found."

    try:
        # Βήμα 1: Προετοιμασία Jelly
        analysis.progress = 20
        analysis.current_step = f"Preparing JavaScript files for {package_name}@{version_param}..."
        analysis.save()

        # Βήμα 2: Κατασκευή Call Graph & Reachability
        analysis.progress = 60
        analysis.current_step = "Building JavaScript Call Graph & Reachability Matrix..."
        analysis.save()

        # Εκτέλεση script
        if package_version:
            subprocess.run(["./analyze_jelly.sh", package_name, package_version], check=True)
        else:
            subprocess.run(["./analyze_jelly.sh", package_name], check=True)

        # Βήμα 3: Ολοκλήρωση
        analysis.progress = 100
        analysis.current_step = "Completed!"
        analysis.status = 'completed'
        analysis.save()

        Notification.objects.create(
            user=analysis.user,
            analysis=analysis,
            message=f"Your jelly analysis for {package_name} ({version_param}) is complete!",
            title="Jelly Analysis Complete",
            link=f"/results/{analysis.id}/"
        )
        return f"Analysis for {package_name} completed."

    except Exception as e:
        analysis.status = 'failed'
        analysis.progress = 0
        analysis.current_step = f"Jelly Failed: {str(e)}"
        analysis.save()

        Notification.objects.create(
            user=analysis.user,
            analysis=analysis,
            title="Jelly Analysis Failed",
            message=f"Η ανάλυση Jelly για το πακέτο {package_name} ({version_param}) απέτυχε.",
            link="/analyses/"
        )
        return f"Jelly failed: {e}"




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
        jelly_script = os.path.join(settings.BASE_DIR, "analyze_jelly.sh")
        ghidra_script = "/home/eva/ghidra-callgraph/ghidra.sh"

        ##Πρόοδος ΒΗΜΑ 1: Gasket Analysis 
        analysis.progress = 10
        analysis.current_step = "Running Gasket Analysis (Extracting Bridges)..."
        analysis.save()

        has_bridges = False  


        if os.path.exists(expected_bridges_file) and os.path.getsize(expected_bridges_file) > 0:
            print(f" [GASKET CACHE HIT] Βρέθηκαν έτοιμα τα bridges: {expected_bridges_file}")
            has_bridges = True
        else:
            print(f" [GASKET CACHE MISS] Εκτέλεση Gasket για {package_name}@{version_param}...")
            try:
                subprocess.run(
                    [gasket_script, package_name, version_param], 
                    cwd=settings.BASE_DIR, 
                    check=True
                )
                if os.path.exists(expected_bridges_file) and os.path.getsize(expected_bridges_file) > 0:
                    print(f" [GASKET SUCCESS] Bridges extracted successfully: {expected_bridges_file}")
                    has_bridges = True
            except Exception as e:
                # Παράλειψη χωρίς fail
                print(f" [GASKET SKIPPED] Gasket failed or no native bindings: {e}")
                has_bridges = False
                analysis.current_step = "No Gasket bridges found, skipping native bridges step..."
                analysis.save()

        # Επιβεβαίωση ότι υπάρχουν πραγματικά bridges μέσα στο αρχείο
        if has_bridges and os.path.exists(expected_bridges_file):
            try:
                with open(expected_bridges_file, 'r', encoding='utf-8') as f:
                    g_data = json.load(f)
                    bridges_list = g_data.get('bridges', [])
                    if not bridges_list or len(bridges_list) == 0:
                        print(f" [INFO] Το {expected_bridges_file} δεν περιέχει bridges.")
                        has_bridges = False
                    else:
                        print(f" [INFO] Εντοπίστηκαν {len(bridges_list)} bridges.")
            except Exception as e:
                print(f" [WARNING] Σφάλμα ανάγνωσης bridges JSON: {e}")
                # Μην το μηδενίζεις αν το αρχείο υπάρχει και έχει περιεχόμενο
                if os.path.getsize(expected_bridges_file) == 0:
                    has_bridges = False


# -------------------------------------------------------------
        # ΒΗΜΑ 2: Εντοπισμός .node αρχείου & Ghidra 
        # -------------------------------------------------------------
        #πρόοδος
        analysis.progress = 35
        analysis.current_step = "Searching for Native .node binary..."
        analysis.save()    


        has_node = False

        jelly_folder = os.path.join(
            settings.BASE_DIR, 
            'static', 
            f'analysis_{package_name}_{version_param}'
        )

        all_node_files = glob.glob(f"{gasket_folder}/**/*.node", recursive=True) + \
                         glob.glob(f"{jelly_folder}/**/*.node", recursive=True) + \
                         glob.glob(f"/home/eva/node_modules/{package_name}/**/*.node", recursive=True)

        if all_node_files:
            has_node = True
            x64_nodes = [f for f in all_node_files if 'x64' in f or 'x86_64' in f or 'linux' in f]
            native_binary_path = x64_nodes[0] if x64_nodes else all_node_files[0]
            print(f"Native binary selected: {native_binary_path}")

            analysis.progress = 50
            analysis.current_step = "Running Ghidra Decompiler on Native Binary..."
            analysis.save()

            if os.path.exists(expected_ghidra_file) and os.path.getsize(expected_ghidra_file) > 0:
                print(f" [GHIDRA CACHE HIT] Βρέθηκε έτοιμη η ανάλυση Ghidra: {expected_ghidra_file}")
            else:
                try:
                    print(f" [GHIDRA RUN] Εκτέλεση Ghidra για {package_name}...")
                    subprocess.run(
                        [ghidra_script, native_binary_path, package_name], 
                        cwd=settings.BASE_DIR, 
                        check=True
                    )
                except Exception as e:
                    # Παράλειψη χωρίς failure
                    print(f" [GHIDRA SKIPPED] Ghidra failed: {e}")
                    analysis.current_step = "Ghidra decompilation failed, proceeding without native symbols..."
                    analysis.save()
        else:
            # Χωρίς .node  (π.χ. WebAssembly / pure JS)
            print(f" [INFO] Δεν βρέθηκε .node binary για το {package_name}. Παράλειψη Ghidra.")
            has_node = False #
            analysis.progress = 50
            analysis.current_step = "No native binary found. Proceeding with WebAssembly/JavaScript..."
            analysis.save()


        #  ΑΠΟΦΑΣΗ: CROSS-LANGUAGE Ή PURE JELLY 
        # -------------------------------------------------------------
        if not has_bridges and not has_node:
            #  ΜΕΤΑΤΡΟΠΗ ΣΕ ΑΠΛΟ JELLY
            print(f" Το πακέτο {package_name} δεν διαθέτει native dependencies. Μετατροπή σε Jelly ανάλυση.")
            
            analysis.analysis_type = 'jelly'
            analysis.progress = 40
            analysis.current_step = "No native dependencies found. Running standard JavaScript call graph..."
            analysis.save()

            # Εκτέλεση απλού Jelly
            subprocess.run([jelly_script, package_name, version_param], cwd=settings.BASE_DIR, check=True)

            analysis.progress = 100
            analysis.current_step = "Completed!"
            analysis.status = 'completed'
            analysis.save()

            Notification.objects.create(
                user=analysis.user if analysis.user else None,
                analysis=analysis,
                title="Analysis Complete",
                message=f"Η ανάλυση για το πακέτο {package_name} ({version_param}) ολοκληρώθηκε επιτυχώς!",
                link=f"/analysis/{analysis.id}/"
            )
            return f"Analysis for {package_name} fell back silently to Jelly and completed."

        # -------------------------------------------------------------
        # 4. ΕΚΤΕΛΕΣΗ CROSS-LANGUAGE JELLY SCRIPT
        # -------------------------------------------------------------
        analysis.progress = 75
        analysis.current_step = "Generating Cross-Language Polyglot Call Graph (Jelly)..."
        analysis.save()

        print(f"Εκτέλεση Cross-Language Jelly για {package_name}@{version_param}...")
        try:
            subprocess.run(
                [cross_script, package_name, version_param], 
                cwd=settings.BASE_DIR, 
                check=True
            )
        except subprocess.CalledProcessError as e:
            analysis.status = 'failed'
            analysis.progress = 0
            analysis.current_step = "Cross-Language Jelly Analysis Failed"
            analysis.save()

            notification_user = analysis.user if analysis.user else None
            Notification.objects.create(
                user=notification_user,
                analysis=analysis,
                title="Cross-Language Analysis Failed",
                message=f"Η ανάλυση Cross-Language για το πακέτο {package_name} ({version_param}) απέτυχε.",
                link="/analyses/"
            )
            return f"Cross-Language Jelly execution failed: {e}"

        
        # ΒΗΜΑ 4: Ολοκλήρωση (100%)
        analysis.progress = 100
        analysis.current_step = "Completed!"
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
        analysis.progress = 0
        analysis.current_step = "Analysis Failed"
        analysis.save()
        print(f"Error running cross-language analysis for {package_name}: {e}")

        # Δημιουργία ειδοποίησης αποτυχίας για να εμφανιστεί στο UI
        notification_user = analysis.user if analysis.user else None
        Notification.objects.create(
            user=notification_user,
            analysis=analysis,
            title="Analysis Failed",
            message=f"Η ανάλυση για το πακέτο {package_name} ({version_param}) απέτυχε: {str(e)}",
            link="/analyses/"
        )

        return f"Analysis failed: {str(e)}"