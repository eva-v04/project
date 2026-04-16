import json
import os

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
            parts = name.split('node_modules/')[-1].split('/')#παίρνουμε το μέρος μετά το node_modules και το χωρίζουμε με /
            if parts[0].startswith('@') and len(parts) > 1: #αν το όνομα ξεκινάει με @ και έχει τουλάχιστον δύο μέρη (π.χ. @types/lodash)
                print("DEBUG βρηκα scoped package:", parts[0], parts[1]) #debug print για να δούμε τα μέρη του scoped package
                pkg_found = f"{parts[0]}/{parts[1]}" #κρατάμε το πρώτο μέρος + το δεύτερο μέρος 
            else:
                print("DEBUG βρηκα regular package:", parts[0]) #debug print για να δούμε τα μέρη του regular package
                pkg_found = parts[0] #αλλιώς κρατάμε μόνο το πρώτο μέρος
        else: #αν το όνομα δεν περιέχει node_modules
            # Περίπτωση Jelly path (π.χ. 'nan/lib/...') ή root πακέτου
            parts = name.split('/') #χωρίζουμε το όνομα με / για να πάρουμε το πρώτο μέρος ή το root πακέτο
            if len(parts) > 0: #αν έχουμε τουλάχιστον ένα μέρος
                first_part = parts[0] #παίρνουμε το πρώτο

                #αν το πρώτο μέρος είναι ένα από τα πακέτα που έχουμε στο lockfile ή είναι το root πακέτο
                if first_part in all_packages or first_part == root_pkg_name:
                    pkg_found = first_part #κρατάμε το πρώτο μέρος ως το πακέτο που βρήκαμε
                    print("DEBUG βρηκα package από Jelly path:", first_part) #debug print για να δούμε το πακέτο που βρήκαμε από το Jelly path
                else:
                    # Αλλιώς θεωρούμε ότι ανήκει στο root πακέτο (π.χ. lib/index.js)
                    pkg_found = root_pkg_name 
                    print("DEBUG θεωρώ ότι ανήκει στο root πακέτο:", root_pkg_name) #debug print για να δούμε ότι θεωρούμε ότι ανήκει στο root πακέτο

                if parts[0].startswith('@') and len(parts) > 1: #αν το όνομα ξεκινάει με @ και έχει τουλάχιστον δύο μέρη (π.χ. @types/lodash)
                    print("DEBUG βρηκα scoped package (Jelly path):", parts[0], parts[1]) #debug print για να δούμε τα μέρη του scoped package
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

    # εκτύπωση Αποτελεσμάτων
    print(f"\n Στατιστικά Ανάλυσης: {os.path.basename(jelly_json_path)}")
    print(f"Τα πακέτα που εντόπισε το Jelly είναι: {reachable_packages}")
    print(f"Συνολικά εγκατεστημένα πακέτα (Lockfile): {total_count}")
    print(f"Πραγματικά προσβάσιμα πακέτα (Reachable): {final_reachable_count}")
    print(f"Ποσοστό Χρήσης: {percentage:.2f}%")
    print(f"Αχρησιμοποίητα πακέτα: {total_count + 1 - final_reachable_count}")

# εκτέλεση
pkg = "sharp"
ver = "0.34.4"

lock_path = f"static/analysis_{pkg}_{ver}/package-lock.json"
jelly_path = f"static/analysis_{pkg}_{ver}/{pkg}.json"

# Περνάμε και το όνομα του root πακέτου ως τρίτο όρισμα
calculate_reachability_packages(lock_path, jelly_path, pkg)