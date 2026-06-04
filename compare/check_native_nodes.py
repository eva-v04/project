import json
import os
import re

def load_json(filepath):
    if not os.path.exists(filepath):
        print(f"Το αρχείο {filepath} δεν βρέθηκε.")
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_coords(loc_str):
    """
    Εξάγει αριθμούς από strings τοποθεσίας.
    Διαχειρίζεται formats όπως '82:4:82:53' ή '2:82:5:82:54'.
    Επιστρέφει λίστα με 4 integers: [start_line, start_col, end_line, end_col]
    """
    numbers = [int(n) for n in re.findall(r'\d+', loc_str)]
    
    # Αν το string περιέχει και το file index στην αρχή (π.χ. "2:82:5:82:54"), 
    # κρατάμε μόνο τα τελευταία 4 νούμερα που αποτελούν το location block
    if len(numbers) >= 4:
        return numbers[-4:]
    return None

def is_exact_modular_match(api_callee_str, graph_str):
    """
    Ευθυγραμμίζει τις στήλες (0-indexed του api_results σε 1-indexed του graph)
    και ελέγχει αν υπάρχει απόλυτη μαθηματική ταύτιση.
    """
    coords_api = extract_coords(api_callee_str)   # π.χ. [82, 4, 82, 53]
    coords_graph = extract_coords(graph_str)       # π.χ. [82, 5, 82, 54]
    
    if not coords_api or not coords_graph:
        return False
        
    api_start_line, api_start_col, api_end_line, api_end_col = coords_api
    graph_start_line, graph_start_col, graph_end_line, graph_end_col = coords_graph
    
    #  Το Jelly γράφει στο JSON προσθέτοντας +1 στις στήλες
    adjusted_api_start_col = api_start_col + 1
    adjusted_api_end_col = api_end_col + 1
    
    # Έλεγχος αν ταιριάζουν απόλυτα γραμμές και ευθυγραμμισμένες στήλες
    return (api_start_line == graph_start_line and
            adjusted_api_start_col == graph_start_col and
            api_end_line == graph_end_line and
            adjusted_api_end_col == graph_end_col)

def check_callee_names_in_json():
    api_results = load_json('api_results.json')
    with_flags = load_json('sqlite3-withflags.json')
    no_flags = load_json('sqlite3-noflags.json')
    
    if not (api_results and with_flags and no_flags):
        return

    print("=" * 70)
    print("ΣΤΑΤΙΣΤΙΚΑ ΣΥΓΚΡΙΣΗΣ ΜΕΓΕΘΟΥΣ ΓΡΑΦΩΝ")
    print("=" * 70)
    funcs_with = len(with_flags.get("functions", {}))
    funcs_no = len(no_flags.get("functions", {}))
    edges_with = len(with_flags.get("call2fun", []))
    edges_no = len(no_flags.get("call2fun", []))
    
    print(f" Συνολικές Συναρτήσεις (With Flags): {funcs_with}")
    print(f" Συνολικές Συναρτήσεις (No Flags):   {funcs_no}")
    print(f"Διαφορά Συναρτήσεων:               +{funcs_with - funcs_no}")
    print("-" * 70)
    print(f" Συνολικές Ακμές call2fun (With Flags): {edges_with}")
    print(f" Συνολικές Ακμές call2fun (No Flags):   {edges_no}")
    print(f"Διαφορά Ακμών:                        +{edges_with - edges_no}")
    print("=" * 70)

    # Συγκέντρωση όλων των τιμών από το sqlite3-withflags.json
    all_graph_strings = []
    for val in with_flags.get("functions", {}).values():
        all_graph_strings.append(str(val))
    for val in with_flags.get("calls", {}).values():
        all_graph_strings.append(str(val))
    for val in with_flags.get("ignore", []):
        all_graph_strings.append(str(val))

    print("\n" + "=" * 70)
    print("ΕΛΕΓΧΟΣ ΑΝΙΧΝΕΥΣΗΣ CALLEE NAMES")
    print("=" * 70)

    total_checked = 0
    total_found = 0
    total_missing = 0

    # Αναζήτηση των Callees από το api_results.json
    for pattern_type, patterns in api_results.items():
        if pattern_type != "call":
            continue
            
        for pattern_name, edges in patterns.items():
            print(f"\nΈλεγχος Pattern API: '{pattern_name}'")
            print("-" * 50)
            
            for edge in edges:
                callee_info = edge.get("callee", {})
                callee_name = callee_info.get("name") # π.χ. "82:4:82:53"
                
                if not callee_name:
                    continue
                
                total_checked += 1
                caller_info = edge.get("caller")
                caller_desc = f"Συνάρτηση {caller_info['name']}" if caller_info else "Top-level Code"
                
                found_in_graph = False
                matched_string_in_graph = ""
                
                # Αναζήτηση με ευθυγράμμιση Off-by-One σφάλματος
                for graph_str in all_graph_strings:
                    if is_exact_modular_match(callee_name, graph_str):
                        found_in_graph = True
                        matched_string_in_graph = graph_str
                        break
                
                if found_in_graph:
                    print(f"ΒΡΕΘΗΚΕ: Το callee '{callee_name}' αντιστοιχεί στο '{matched_string_in_graph}' του γράφου")
                    print(f"   └─ Caller: {caller_desc} -> Τοποθεσία: {callee_info.get('loc')}")
                    total_found += 1
                else:
                    print(f"ΛΕΙΠΕΙ:  Το callee '{callee_name}' ΔΕΝ αντιστοιχεί σε καμία εγγραφή!")
                    print(f"   └─ Caller: {caller_desc} -> Τοποθεσία: {callee_info.get('loc')}")
                    total_missing += 1

    print("\n" + "=" * 70)
    print("ΤΕΛΙΚΟ ΑΠΟΤΕΛΕΣΜΑ")
    print(f"• Συνολικά Callee Names που ελέγχθηκαν: {total_checked}")
    print(f"• Callee Names που ΕΝΣΩΜΑΤΩΘΗΚΑΝ σωστά: {total_found}")
    print(f"• Callee Names που ΛΕΙΠΟΥΝ από το πλάνο: {total_missing}")
    if total_checked > 0:
        print(f"• Ποσοστό Επιτυχίας Ανάλυσης: {(total_found / total_checked) * 100:.2f}%")
    print("=" * 70)

if __name__ == "__main__":
    check_callee_names_in_json()