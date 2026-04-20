import json
import os
import re #regex για επίπεδο συναρτήσεων
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')
import io
import base64


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#def generate_full_stats(pkg, ver):
    # Χρησιμοποιούμε το BASE_DIR για να βρούμε σίγουρα τον φάκελο static
    #analysis_folder = os.path.join(BASE_DIR, 'static', f"analysis_{pkg}_{ver}")


def calculate_reachability_packages(lock_file_path, jelly_json_path, root_pkg_name):
    # Φόρτωση του package-lock.json
    try:
        with open(lock_file_path, 'r', encoding='utf-8') as f:
            lock_data = json.load(f)
    except FileNotFoundError:
        print(f"Σφάλμα: Δεν βρέθηκε το αρχείο {lock_file_path}")
        return

    all_packages = set() #εδώ θα αποθηκεύονται τα ονόματα των πακέτων από το lockfile
    #set για μοναδικότητα
    packages_dict = lock_data.get('packages', {})
    for path in packages_dict.keys(): #για κάθε μονοπάτι
        if path.startswith("node_modules/"): #αν ξεκινάει με node_modules/
            pkg_name = path.replace('node_modules/', '', 1) #το αφαιρούμε και κρατάμε μόνο το όνομα
            if pkg_name:
                all_packages.add(pkg_name)

    #Φόρτωση του JSON που έχει φτιάξει το Jelly (π.χ. sqlite3.json)
    try:
        with open(jelly_json_path, 'r', encoding='utf-8') as f:
            jelly_data = json.load(f)
    except FileNotFoundError:
        print(f"Σφάλμα: Δεν βρέθηκε το αρχείο {jelly_json_path}")
        return

    reachable_packages = set() #εδώ θα αποθηκεύονται τα ονόματα των πακέτων που εντόπισε το Jelly ως reachable
    files_list = jelly_data.get('files', []) #παίρνει τη λίστα files από το JSON του Jelly
    
    for name in files_list: #για κάθε όνομα αρχείου
        if not isinstance(name, str): continue #αν δεν είναι string το αγνοούμε
        
        name = name.replace('\\', '/') # Κανονικοποίηση για Windows/Linux
        pkg_found = None #αρχικοποίηση μεταβλητής για το πακέτο που θα βρούμε

        #είμαστε ήδη στο Node_modules, άρα για να βγει True, πρέπει το path να είναι node_modules/node_modules/...
        if 'node_modules/' in name:
            parts = name.split('node_modules/')[-1].split('/')#παίρνουμε το μέρος μετά το node_modules και το χωρίζουμε με /
            if parts[0].startswith('@') and len(parts) > 1: #αν το όνομα ξεκινάει με @ και έχει τουλάχιστον δύο μέρη (π.χ. @types/lodash)
                #print("DEBUG βρηκα scoped package:", parts[0], parts[1]) #debug print για να δούμε τα μέρη του scoped package
                pkg_found = f"{parts[0]}/{parts[1]}" #κρατάμε το πρώτο μέρος + το δεύτερο μέρος 
            else:
                #print("DEBUG βρηκα regular package:", parts[0]) #debug print για να δούμε τα μέρη του regular package
                pkg_found = parts[0] #αλλιώς κρατάμε μόνο το πρώτο μέρος
        else: #αν το όνομα δεν περιέχει node_modules
            # Περίπτωση Jelly path (π.χ. 'nan/lib/...') ή root πακέτου
            parts = name.split('/') #χωρίζουμε το όνομα με / για να πάρουμε το πρώτο μέρος ή το root πακέτο
            if len(parts) > 0: #αν έχουμε τουλάχιστον ένα μέρος
                first_part = parts[0] #παίρνουμε το πρώτο

                #αν το πρώτο μέρος είναι ένα από τα πακέτα που έχουμε στο lockfile ή είναι το root πακέτο
                if first_part in all_packages or first_part == root_pkg_name:
                    pkg_found = first_part #κρατάμε το πρώτο μέρος ως το πακέτο που βρήκαμε
                    #print("DEBUG βρηκα package από Jelly path:", first_part) #debug print για να δούμε το πακέτο που βρήκαμε από το Jelly path
                else:
                    # Αλλιώς θεωρούμε ότι ανήκει στο root πακέτο (π.χ. lib/index.js)
                    pkg_found = root_pkg_name 
                    #print("DEBUG θεωρώ ότι ανήκει στο root πακέτο:", root_pkg_name) #debug print για να δούμε ότι θεωρούμε ότι ανήκει στο root πακέτο

                if parts[0].startswith('@') and len(parts) > 1: #αν το όνομα ξεκινάει με @ και έχει τουλάχιστον δύο μέρη (π.χ. @types/lodash)
                    #print("DEBUG βρηκα scoped package (Jelly path):", parts[0], parts[1]) #debug print για να δούμε τα μέρη του scoped package
                    pkg_found = f"{parts[0]}/{parts[1]}" #κρατάμε το πρώτο μέρος + το δεύτερο μέρος 
            
        if pkg_found:
            reachable_packages.add(pkg_found) #προσθέτουμε το πακέτο που βρήκαμε στα reachable_packages

    #  Υπολογισμοί και Σύγκριση
    # Βρίσκουμε ποιες από τις εξαρτήσεις του lockfile είναι reachable
    final_reachable = reachable_packages.intersection(all_packages)
    
    # Προσθέτουμε το root πακέτο (πχ.sqlite3)
    if root_pkg_name in reachable_packages:
        final_reachable.add(root_pkg_name)

    total_count = len(all_packages)
    final_reachable_count = len(final_reachable)
    # Ποσοστό του συνόλου των εγκατεστημένων + το root πακέτο
    percentage = (final_reachable_count / (total_count + 1) * 100) if total_count > 0 else 0

    return {
        "total_packages": total_count + 1,
        "reachable_packages": final_reachable_count,
        "package_percentage": round(percentage, 2),
        "unused_packages": (total_count + 1) - final_reachable_count
    }
    # εκτύπωση Αποτελεσμάτων
    print(f"\n Στατιστικά Ανάλυσης Πακέτων: {os.path.basename(jelly_json_path)}")
    print(f"Τα πακέτα που εντοπίστηκαν είναι: {reachable_packages}")
    print(f"Συνολικά εγκατεστημένα πακέτα: {total_count}")
    print(f"Πραγματικά προσβάσιμα πακέτα (Reachable): {final_reachable_count}")
    print(f"Ποσοστό Χρήσης: {percentage:.2f}%")
    print(f"Αχρησιμοποίητα πακέτα: {total_count + 1 - final_reachable_count}") #+1 για το root πακέτο


def calculate_reachability_files(analysis_dir, jelly_json_path):
    # Καταμέτρηση ΟΛΩΝ των αρχείων 
    all_physical_files = set()
    node_modules_path = os.path.join(analysis_dir, "node_modules")
    
    if not os.path.exists(node_modules_path):
        print(f"Σφάλμα: Δεν βρέθηκε ο φάκελος {node_modules_path}")
        return

    for root, dirs, files in os.walk(node_modules_path):
        for file in files:
            if file.endswith(('.js', '.json', '.node', '.mjs', '.cjs')):
                full_path = os.path.join(root, file)
                # Σχετικό path ως προς το analysis_dir (π.χ. node_modules/sharp/...)
                rel_path = os.path.relpath(full_path, analysis_dir).replace('\\', '/')
                all_physical_files.add(rel_path)

    # Φόρτωση από Jelly
    try:
        with open(jelly_json_path, 'r', encoding='utf-8') as f:
            jelly_data = json.load(f)
    except FileNotFoundError:
        return

    reachable_files = set()
    for name in jelly_data.get('files', []):
        clean_name = name.replace('\\', '/')
        # Ταύτιση Jelly path με Physical path (endswith)
        found_match = False
        for phys_f in all_physical_files:
            if phys_f.endswith(clean_name):
                reachable_files.add(phys_f)
                found_match = True
                break
        if not found_match:
             # Αν το Jelly έχει ήδη το σωστό path
             if clean_name in all_physical_files:
                 reachable_files.add(clean_name)

    total_count = len(all_physical_files)
    reachable_count = len(reachable_files) 
    percentage = (reachable_count / total_count * 100) if total_count > 0 else 0

    return {
        "total_files": total_count,
        "reachable_files": reachable_count,
        "file_percentage": round(percentage, 2),
        "unused_files": total_count - reachable_count
    }

    print(f"\n Στατιστικά Ανάλυσης Αρχείων: {os.path.basename(jelly_json_path)}")
    print(f"Συνολικά αρχεία στο node_modules: {total_count}")
    print(f"Πραγματικά προσβάσιμα αρχεία (Reachable): {reachable_count}")
    print(f"Ποσοστό Χρήσης Αρχείων: {percentage:.2f}%")
    print(f"Αχρησιμοποίητα αρχεία: {total_count - reachable_count}")


def count_functions_in_file(file_path):
    """
    Χρησιμοποιεί Regex για να μετρήσει ορισμούς συναρτήσεων σε ένα αρχείο JS.
    """
    total = 0
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # 1. Κανονικές συναρτήσεις: function name() ή function()
            # 2. Arrow functions: (args) => { ... }
            # 3. Μέθοδοι κλάσεων: name(args) { ... }
            patterns = [
                r'\bfunction\s*[\w$]*\s*\(', # function declarations
                r'=\s*\([^)]*\)\s*=>',       # arrow functions
                r'\b[\w$]+\s*\([^)]*\)\s*\{'  # class methods / object shorthand
            ]
            for pattern in patterns:
                matches = re.findall(pattern, content)
                total += len(matches)
    except Exception:
        pass # Αγνοούμε αρχεία που δεν διαβάζονται (π.χ. binary)
    return total


def calculate_reachability_functions(analysis_dir, jelly_json_path):
    # Καταμέτρηση ΟΛΩΝ των συναρτήσεων που υπάρχουν στο node_modules
    total_functions_in_disk = 0
    node_modules_path = os.path.join(analysis_dir, "node_modules")
    
    if not os.path.exists(node_modules_path):
        print("Σφάλμα: Δεν βρέθηκε ο φάκελος node_modules")
        return

    #print("Σάρωση αρχείων για καταμέτρηση συνολικών συναρτήσεων")
    for root, dirs, files in os.walk(node_modules_path):
        for file in files:
            if file.endswith(('.js', '.mjs', '.cjs')):
                full_path = os.path.join(root, file)
                total_functions_in_disk += count_functions_in_file(full_path)

    # Φόρτωση Προσβάσιμων (Reachable) συναρτήσεων από το Jelly
    try:
        with open(jelly_json_path, 'r', encoding='utf-8') as f:
            jelly_data = json.load(f)
    except FileNotFoundError:
        return

    # Το Jelly έχει έτοιμο το πλήθος των συναρτήσεων στο κλειδί "functions"
    functions_dict = jelly_data.get('functions', {})
    reachable_functions_count = len(functions_dict)

    # Υπολογισμοί
    percentage = (reachable_functions_count / total_functions_in_disk * 100) if total_functions_in_disk > 0 else 0

    return {
        "total_functions": total_functions_in_disk,
        "reachable_functions": reachable_functions_count,
        "function_percentage": round(percentage, 2),
        "unused_functions": total_functions_in_disk - reachable_functions_count
    }
    print(f"\nΣτατιστικά Ανάλυσης Συναρτήσεων: {os.path.basename(jelly_json_path)}")
    print(f"Συνολικές συναρτήσεις στον κώδικα (στατική εκτίμηση): {total_functions_in_disk}")
    print(f"Πραγματικά προσβάσιμες συναρτήσεις (από Jelly): {reachable_functions_count}")
    print(f"Ποσοστό Χρήσης Συναρτήσεων: {percentage:.2f}%")
    print(f"Αχρησιμοποίητες συναρτήσεις: {total_functions_in_disk - reachable_functions_count}")


def generate_full_stats(pkg, ver):
    analysis_folder = os.path.join(BASE_DIR, 'static', f"analysis_{pkg}_{ver}")
    lock_path = os.path.join(analysis_folder, "package-lock.json")
    jelly_path = os.path.join(analysis_folder, f"{pkg}.json")

    if not os.path.exists(analysis_folder):
        print(f"Error: Folder {analysis_folder} not found!")
        return None
        
    # Συλλογή όλων των αποτελεσμάτων σε ένα dictionary
    full_report = {
        "package_stats": calculate_reachability_packages(lock_path, jelly_path, pkg),
        "file_stats": calculate_reachability_files(analysis_folder, jelly_path),
        "function_stats": calculate_reachability_functions(analysis_folder, jelly_path)
    }

    # Αποθήκευση σε stats.json
    output_path = os.path.join(analysis_folder, 'stats.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(full_report, f, indent=4, ensure_ascii=False)
    
    return full_report



def get_matplotlib_graph(reachable, total):

    plt.clf() # Καθαρίζει το προηγούμενο γράφημα
    if total == 0: return ""

    # Δεδομένα
    labels = ['Used', 'Unused']
    sizes = [reachable, total - reachable]
    colors = ['#00d2ff', '#1e293b']

    # Δημιουργία Plot
    fig, ax = plt.subplots(figsize=(5, 4), facecolor='none')
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors, textprops={'color':"white"})
    
    # Μετατροπή σε εικόνα στη μνήμη
    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True)
    buf.seek(0)
    
    # Μετατροπή σε Base64 string
    string = base64.b64encode(buf.read())
    uri = string.decode('utf-8')
    plt.close(fig)
    return uri

# εκτέλεση
#pkg = "sqlite3"
#ver = "6.0.1"

#analysis_folder = f"static/analysis_{pkg}_{ver}"

#lock_path = f"static/analysis_{pkg}_{ver}/package-lock.json"
#jelly_path = f"static/analysis_{pkg}_{ver}/{pkg}.json"

#calculate_reachability_packages(lock_path, jelly_path, pkg)
#calculate_reachability_files(analysis_folder, jelly_path)
#calculate_reachability_functions(analysis_folder, jelly_path)