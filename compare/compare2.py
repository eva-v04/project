import json

def find_jelly_differences():
    old_jelly_file = "sqlite3.json"
    new_jelly_file = "sqlite3-withflags.json"
    
    print("=== Ανάλυση Διαφορών: Νέο JSON vs Παλιό JSON ===\n")
    
    with open(old_jelly_file, 'r', encoding='utf-8') as f:
        old_data = json.load(f)
    with open(new_jelly_file, 'r', encoding='utf-8') as f:
        new_data = json.load(f)

    #Εύρεση νέων Functions (υπάρχουν στο νέο, αλλά όχι στο παλιό)
    old_functions = old_data.get("functions", {})
    new_functions = new_data.get("functions", {})
    
    # Φιλτράρουμε με βάση την τιμή (το location string), όχι το ID, 
    # γιατί τα IDs μπορεί να άλλαξαν σειρά.
    old_func_values = set(old_functions.values())
    
    new_functions_added = {}
    for f_id, f_str in new_functions.items():
        if f_str not in old_func_values:
            new_functions_added[f_id] = f_str

    #Εύρεση νέων ακμών στο fun2fun
    # Μετατρέπουμε τις λίστες [caller, callee] σε tuples για να μπορούμε να κάνουμε set operations
    old_fun2fun = set(tuple(edge) for edge in old_data.get("fun2fun", []))
    new_fun2fun = old_data.get("fun2fun", []) # κρατάμε την αρχική λίστα για έλεγχο
    
    # Διαβάζουμε τις πραγματικές ακμές του νέου αρχείου
    actual_new_fun2fun = [edge for edge in new_data.get("fun2fun", [])]
    fun2fun_added = [edge for edge in actual_new_fun2fun if tuple(edge) not in old_fun2fun]

    #Εύρεση νέων ακμών στο call2fun
    old_call2fun = set(tuple(edge) for edge in old_data.get("call2fun", []))
    actual_new_call2fun = [edge for edge in new_data.get("call2fun", [])]
    call2fun_added = [edge for edge in actual_new_call2fun if tuple(edge) not in old_call2fun]

    # === ΕΜΦΑΝΙΣΗ ΑΠΟΤΕΛΕΣΜΑΤΩΝ ΣΕ FORMAT JSON ===

    # Α) Νέα Functions
    print(f"=== ΝΕΑ FUNCTIONS ΠΟΥ ΠΡΟΣΤΕΘΗΚΑΝ ({len(new_functions_added)} εγγραφές) ===")
    if new_functions_added:
        # indent=2 για όμορφη στοίχιση ακριβώς όπως στο JSON αρχείο
        print(json.dumps(new_functions_added, indent=2, ensure_ascii=False))
    else:
        print("{}")
        
    print("\n" + "="*60 + "\n")

    # Β) Νέες ακμές στο fun2fun
    print(f"=== ΝΕΕΣ ΑΚΜΕΣ ΣΤΟ fun2fun ΠΟΥ ΠΡΟΣΤΕΘΗΚΑΝ ({len(fun2fun_added)} ακμές) ===")
    if fun2fun_added:
        print(json.dumps(fun2fun_added))
    else:
        print("[]")
        
    print("\n" + "="*60 + "\n")

    # Γ) Νέες ακμές στο call2fun
    print(f"=== ΝΕΕΣ ΑΚΜΕΣ ΣΤΟ call2fun ΠΟΥ ΠΡΟΣΤΕΘΗΚΑΝ ({len(call2fun_added)} ακμές) ===")
    if call2fun_added:
        print(json.dumps(call2fun_added))
    else:
        print("[]")

if __name__ == "__main__":
    find_jelly_differences()