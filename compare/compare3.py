import json

def find_removed_jelly_differences():
    old_jelly_file = "sqlite3.json"
    new_jelly_file = "sqlite3-withflags.json"
    
    print("=== Ανάλυση Αφαιρέσεων: Τι υπήρχε στο Παλιό και ΛΕΙΠΕΙ από το Νέο ===\n")
    
    with open(old_jelly_file, 'r', encoding='utf-8') as f:
        old_data = json.load(f)
    with open(new_jelly_file, 'r', encoding='utf-8') as f:
        new_data = json.load(f)

    #  Εύρεση Functions που αφαιρέθηκαν (υπάρχουν στο παλιό, αλλά όχι στο νέο)
    old_functions = old_data.get("functions", {})
    new_functions = new_data.get("functions", {})
    
    # Φιλτράρουμε με βάση την τιμή (το location string)
    new_func_values = set(new_functions.values())
    
    functions_removed = {}
    for f_id, f_str in old_functions.items():
        if f_str not in new_func_values:
            functions_removed[f_id] = f_str

    # Εύρεση ακμών fun2fun που αφαιρέθηκαν
    # Μετατρέπουμε τις νέες ακμές σε tuples για γρήγορο set operation
    new_fun2fun = set(tuple(edge) for edge in new_data.get("fun2fun", []))
    actual_old_fun2fun = [edge for edge in old_data.get("fun2fun", [])]
    
    # Κρατάμε όσες παλιές ακμές ΔΕΝ υπάρχουν στο νέο σετ
    fun2fun_removed = [edge for edge in actual_old_fun2fun if tuple(edge) not in new_fun2fun]

    #  Εύρεση ακμών call2fun που αφαιρέθηκαν
    new_call2fun = set(tuple(edge) for edge in new_data.get("call2fun", []))
    actual_old_call2fun = [edge for edge in old_data.get("call2fun", [])]
    
    call2fun_removed = [edge for edge in actual_old_call2fun if tuple(edge) not in new_call2fun]

    # === ΕΜΦΑΝΙΣΗ ΑΠΟΤΕΛΕΣΜΑΤΩΝ ΣΕ FORMAT JSON ===

    # Α) Functions που Αφαιρέθηκαν
    print(f"=== FUNCTIONS ΠΟΥ ΑΦΑΙΡΕΘΗΚΑΝ / ΔΙΟΡΘΩΘΗΚΑΝ ({len(functions_removed)} εγγραφές) ===")
    if functions_removed:
        print(json.dumps(functions_removed, indent=2, ensure_ascii=False))
    else:
        print("{}")
        
    print("\n" + "="*60 + "\n")

    # Β) Ακμές fun2fun που Αφαιρέθηκαν
    print(f"=== ΑΚΜΕΣ ΣΤΟ fun2fun ΠΟΥ ΑΦΑΙΡΕΘΗΚΑΝ ({len(fun2fun_removed)} ακμές) ===")
    if fun2fun_removed:
        print(json.dumps(fun2fun_removed))
    else:
        print("[]")
        
    print("\n" + "="*60 + "\n")

    # Γ) Ακμές call2fun που Αφαιρέθηκαν
    print(f"=== ΑΚΜΕΣ ΣΤΟ call2fun ΠΟΥ ΑΦΑΙΡΕΘΗΚΑΝ ({len(call2fun_removed)} ακμές) ===")
    if call2fun_removed:
        print(json.dumps(call2fun_removed))
    else:
        print("[]")

if __name__ == "__main__":
    find_removed_jelly_differences()