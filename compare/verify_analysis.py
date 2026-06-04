import json
import os

def run_verification():
    # Έλεγχος ύπαρξης των αρχείων παραγωγής
    files = ['api_results.json', 'sqlite3-noflags.json', 'sqlite3-withflags.json']
    for f in files:
        if not os.path.exists(f):
            print(f"[-] Σφάλμα: Το αρχείο {f} δεν βρέθηκε στο τρέχον μονοπάτι.")
            return

    with open('api_results.json', 'r', encoding='utf-8') as f:
        api_results = json.load(f)
    with open('sqlite3-withflags.json', 'r', encoding='utf-8') as f:
        withflags = json.load(f)
    with open('sqlite3-noflags.json', 'r', encoding='utf-8') as f:
        noflags = json.load(f)

    print("="*60)
    print("   ΣΤΑΤΙΣΤΙΚΟΣ ΕΛΕΓΧΟΣ ΚΑΙ ΕΠΑΛΗΘΕΥΣΗ NATIVE ΑΝΑΛΥΣΗΣ")
    print("="*60)

    # 1. Ανάλυση του api_results.json
    print("\n=== 1. ΑΝΑΛΥΣΗ ΑΡΧΕΙΟΥ api_results.json ===")
    total_api = 0
    for key, val in api_results.items():
        count = sum(len(locs) for locs in val.values())
        print(f"  • Κατηγορία '{key}': {count} στατικές τοποθεσίες")
        total_api += count
    print(f"  --> ΣΥΝΟΛΟ Αναμενόμενων Στατικών Τοποθεσιών (API Usage): {total_api}")

    # 2. Σύγκριση Κόμβων (Functions)
    print("\n=== 2. ΣΥΓΚΡΙΣΗ ΚΟΜΒΩΝ ΓΡΑΦΟΥ (Functions) ===")
    print(f"  • Κόμβοι χωρίς Flags (sqlite3-noflags): {len(noflags['functions'])}")
    print(f"  • Κόμβοι με Flags (sqlite3-withflags): {len(withflags['functions'])}")
    
    native_funcs = {k: v for k, v in withflags['functions'].items() if v.startswith('[Native]:')}
    print(f"  • Νέοι Εικονικοί Native Κόμβοι που εντοπίστηκαν: {len(native_funcs)}")
    print(f"  • Μοναδικές Native Υπογραφές (Signatures): {len(set(native_funcs.values()))}")

    # 3. Ανάλυση Ακμών (Call Graph Edges)
    print("\n=== 3. ΣΥΓΚΡΙΣΗ ΑΚΜΩΝ ΚΛΗΣΕΩΝ (Call Graph Edges) ===")
    print(f"  • Συνολικές ακμές call2fun (No Flags): {len(noflags['call2fun'])}")
    print(f"  • Συνολικές ακμές call2fun (With Flags): {len(withflags['call2fun'])}")
    print(f"  • Συνολικές ακμές fun2fun (No Flags): {len(noflags['fun2fun'])}")
    print(f"  • Συνολικές ακμές fun2fun (With Flags): {len(withflags['fun2fun'])}")
    
    native_ids = {int(k) for k in native_funcs.keys()}
    c2f_native = [e for e in withflags['call2fun'] if e[1] in native_ids]
    f2f_native = [e for e in withflags['fun2fun'] if e[1] in native_ids]
    
    print(f"  • Ακμές Call-to-Function προς Native προορισμούς: {len(c2f_native)}")
    print(f"  • Ακμές Function-to-Function προς Native προορισμούς: {len(f2f_native)}")
    
    print("\n" + "="*60)
    print("=== ΣΥΜΠΕΡΑΣΜΑ ===")
    print(f"διαφορα στο call2fun: {len(withflags['call2fun']) - len(noflags['call2fun'])}")
    print(f"φιαφορά στο fun2fun: {len(withflags['fun2fun']) - len(noflags['fun2fun'])}")
    print(f"διαφορά στο functions: {len(withflags['functions']) - len(noflags['functions'])}")

if __name__ == '__main__':
    run_verification()