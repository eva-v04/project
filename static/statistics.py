import json
import os

def calculate_reachability(lock_file_path, jelly_json_path):
    # 1. Φόρτωση του package-lock.json
    try:
        with open(lock_file_path, 'r', encoding='utf-8') as f:
            lock_data = json.load(f)
    except FileNotFoundError:
        print(f"Σφάλμα: Δεν βρέθηκε το αρχείο {lock_file_path}")
        return

    all_packages = set()
    # Στο package-lock v2/v3 τα πακέτα είναι στο "packages"
    packages_dict = lock_data.get('packages', {})
    for path in packages_dict.keys():
        if path == "" or not path.startswith("node_modules/"): 
            continue
        
        # Καθαρισμός: "node_modules/abbrev" -> "abbrev"
        pkg_name = path.replace('node_modules/', '', 1)
        if pkg_name:
            all_packages.add(pkg_name)

    # 2. Φόρτωση του sqlite3.json
    try:
        with open(jelly_json_path, 'r', encoding='utf-8') as f:
            jelly_data = json.load(f)
    except FileNotFoundError:
        print(f"Σφάλμα: Δεν βρέθηκε το αρχείο {jelly_json_path}")
        return

    reachable_packages = set()
    
    # ΠΡΟΣΟΧΗ: Στο δικό σου αρχείο το "files" είναι λίστα από objects {"name": "..."}
    files_list = jelly_data.get('files', [])
    
    for file_obj in files_list:
        # Παίρνουμε το string από το κλειδί "name"
        name = file_obj.get('name', '')
        
        if 'node_modules/' in name:
            # Απομονώνουμε το κομμάτι μετά το node_modules/
            parts = name.split('node_modules/')[-1].split('/')
            
            if parts[0].startswith('@'):
                # Scoped package: @owner/package
                pkg_name = f"{parts[0]}/{parts[1]}"
            else:
                pkg_name = parts[0]
                
            reachable_packages.add(pkg_name)

    # 3. Υπολογισμοί
    total_count = len(all_packages)
    reachable_count = len(reachable_packages)
    # Υπολογίζουμε μόνο όσα υπάρχουν όντως στο lockfile (για σιγουριά)
    final_reachable = reachable_packages.intersection(all_packages)
    final_reachable_count = len(final_reachable)
    
    percentage = (final_reachable_count / total_count * 100) if total_count > 0 else 0

    # 4. Εκτύπωση
    print(f"\n--- Στατιστικά Ανάλυσης: {os.path.basename(jelly_json_path)} ---")
    print(f"Συνολικά εγκατεστημένα πακέτα στο node_modules: {total_count}")
    print(f"Πραγματικά προσβάσιμα πακέτα (Reachable): {final_reachable_count}")
    print(f"Ποσοστό Χρήσης: {percentage:.2f}%")
    print(f"Αχρησιμοποίητα πακέτα: {total_count - final_reachable_count}")

# --- ΕΚΤΕΛΕΣΗ ---
# Αντικατάστησε το 'PACKAGE' και 'VERSION' με τα δικά σου
pkg = "sqlite3"
ver = "5.1.7"

# Δυναμικό path προς τα αρχεία σου
lock_path = f"static/analysis_{pkg}_{ver}/package-lock.json"
jelly_path = f"static/analysis_{pkg}_{ver}/sqlite3.json"

calculate_reachability(lock_path, jelly_path)