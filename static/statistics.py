import json
import os

def calculate_reachability(lock_file_path, jelly_json_path, root_pkg_name):
    # Φόρτωση του package-lock.json
    try:
        with open(lock_file_path, 'r', encoding='utf-8') as f:
            lock_data = json.load(f)
    except FileNotFoundError:
        print(f"Σφάλμα: Δεν βρέθηκε το αρχείο {lock_file_path}")
        return

    all_packages = set() 
    packages_dict = lock_data.get('packages', {})
    for path in packages_dict.keys():
        if path.startswith("node_modules/"):
            # Μετατροπή "node_modules/abbrev" -> "abbrev"
            pkg_name = path.replace('node_modules/', '', 1)
            if pkg_name:
                all_packages.add(pkg_name)

    #  Φόρτωση του JSON που έχει φτιάξει το Jelly (π.χ. sqlite3.json)
    try:
        with open(jelly_json_path, 'r', encoding='utf-8') as f:
            jelly_data = json.load(f)
    except FileNotFoundError:
        print(f"Σφάλμα: Δεν βρέθηκε το αρχείο {jelly_json_path}")
        return

    reachable_packages = set()
    files_list = jelly_data.get('files', [])
    
    for name in files_list:
        if not isinstance(name, str): continue
        
        name = name.replace('\\', '/') # Κανονικοποίηση για Windows/Linux
        pkg_found = None

        if 'node_modules/' in name:
            # Περίπτωση εξάρτησης μέσα στο node_modules
            parts = name.split('node_modules/')[-1].split('/')
            if parts[0].startswith('@') and len(parts) > 1:
                pkg_found = f"{parts[0]}/{parts[1]}"
            else:
                pkg_found = parts[0]
        else:
            # Περίπτωση Jelly path (π.χ. 'nan/lib/...') ή root πακέτου
            parts = name.split('/')
            if len(parts) > 0:
                first_part = parts[0]
                # Αν το πρώτο μέρος υπάρχει στο lockfile ή είναι το root
                if first_part in all_packages or first_part == root_pkg_name:
                    pkg_found = first_part
                else:
                    # Αλλιώς θεωρούμε ότι ανήκει στο root πακέτο (π.χ. lib/index.js)
                    pkg_found = root_pkg_name
        
        if pkg_found:
            reachable_packages.add(pkg_found)

    #  Υπολογισμοί και Σύγκριση
    # Βρίσκουμε ποιες από τις εξαρτήσεις του lockfile είναι reachable
    final_reachable = reachable_packages.intersection(all_packages)
    
    # Προσθέτουμε το root πακέτο (πχ.sqlite3) αν εντοπίστηκε
    if root_pkg_name in reachable_packages:
        final_reachable.add(root_pkg_name)

    total_count = len(all_packages)
    final_reachable_count = len(final_reachable)
    
    # Ποσοστό του συνόλου των εγκατεστημένων + το root πακέτο
    percentage = (final_reachable_count / (total_count + 1) * 100) if total_count > 0 else 0

    # εκτύπωση Αποτελεσμάτων
    print(f"\n--- Στατιστικά Ανάλυσης: {os.path.basename(jelly_json_path)} ---")
    print(f"DEBUG: Τα πακέτα που εντόπισε το Jelly είναι: {reachable_packages}")
    print(f"Συνολικά εγκατεστημένα πακέτα (Lockfile): {total_count}")
    print(f"Πραγματικά προσβάσιμα πακέτα (Reachable): {final_reachable_count}")
    print(f"Ποσοστό Χρήσης: {percentage:.2f}%")
    print(f"Αχρησιμοποίητα πακέτα: {total_count + 1 - final_reachable_count}")

# εκτέλεση
pkg = "sqlite3"
ver = "6.0.1"

lock_path = f"static/analysis_{pkg}_{ver}/package-lock.json"
jelly_path = f"static/analysis_{pkg}_{ver}/sqlite3.json"

# Περνάμε και το όνομα του root πακέτου ως τρίτο όρισμα
calculate_reachability(lock_path, jelly_path, pkg)