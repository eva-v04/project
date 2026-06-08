import json
import os
from thefuzz import fuzz

def clean_jelly_pattern(pattern):
    """Καθαρίζει το string του Jelly για να μείνουν μόνο τα ουσιαστικά ονόματα"""
    # Αφαίρεση των προθεμάτων [Call], [Read], [Write], [Import]
    if "] " in pattern:
        pattern = pattern.split("] ")[1]
    # Αφαίρεση παρενθέσεων και brackets
    pattern = pattern.replace("<bindings>().", "").replace("<sqlite3/lib/sqlite3-binding>.", "")
    pattern = pattern.replace("()", "").replace(".prototype", "")
    return pattern.strip()

def clean_gasket_name(jsname):
    """Καθαρίζει το jsname του Gasket"""
    # Κρατάμε μόνο το κομμάτι μετά το Release ή το lib/sqlite3
    if "Release/" in jsname:
        jsname = jsname.split("Release/")[1]
    elif "sqlite3/" in jsname:
        jsname = jsname.split("sqlite3/")[1]
    jsname = jsname.replace(".prototype", "")
    return jsname.strip()

def run_fuzzy_matching():
    # Φόρτωση των αρχείων
    with open('api_results.json', 'r', encoding='utf-8') as f:
        jelly_data = json.load(f)
    with open('bridges_sqlite3.json', 'r', encoding='utf-8') as f:
        gasket_data = json.load(f)

    # Μάζεμα όλων των patterns από το Jelly
    jelly_patterns = []
    for category in jelly_data.values():
        for pattern in category.keys():
            jelly_patterns.append(pattern)
    # Αφαίρεση διπλότυπων patterns
    jelly_patterns = list(set(jelly_patterns))

    # Μάζεμα των bridges από το Gasket
    gasket_bridges = gasket_data.get("bridges", [])

    print("=" * 70)
    print("   ΕΝΑΡΞΗ FUZZY MATCHING (JELLY PATTERNS <-> GASKET BRIDGES)")
    print("=" * 70)

    matches_found = 0
    results_mapping = []

    for j_pattern in jelly_patterns:
        cleaned_jelly = clean_jelly_pattern(j_pattern)
        
        best_score = 0
        best_match = None

        for bridge in gasket_bridges:
            cleaned_gasket = clean_gasket_name(bridge["jsname"])
            
            # Υπολογισμός ομοιότητας με 2 μεθόδους της thefuzz
            # Το partial_ratio είναι εξαιρετικό για substrings (π.χ. αν το ένα περιέχει το άλλο)
            score = fuzz.partial_ratio(cleaned_jelly.lower(), cleaned_gasket.lower())
            
            if score > best_score:
                best_score = score
                best_match = bridge

        # Θέτουμε ένα όριο (threshold) π.χ. 75% ομοιότητα για να θεωρηθεί έγκυρο match
        if best_score >= 75 and best_match:
            matches_found += 1
            print(f"\n[✔] MATCH FOUND ({best_score}%)")
            print(f"    Jelly:  {j_pattern} (Clean: {cleaned_jelly})")
            print(f"    Gasket: {best_match['jsname']} -> C++: {best_match['cfunc']}")
            
            results_mapping.append({
                "jelly_pattern": j_pattern,
                "gasket_jsname": best_match['jsname'],
                "cfunc": best_match['cfunc'],
                "score": best_score
            })
        else:
            print(f"\n[-] NO GOOD MATCH FOR: {j_pattern} (Best score was {best_score}%)")

    print("\n" + "=" * 70)
    print(f"   ΣΤΑΤΙΣΤΙΚΑ: Βρέθηκαν {matches_found} πετυχημένα matches!")
    print("=" * 70)

    # Αποθήκευση των αποτελεσμάτων σε ένα νέο αρχείο mapping
    with open('jelly_to_cfunc_mapping.json', 'w', encoding='utf-8') as outfile:
        json.dump(results_mapping, outfile, indent=2, ensure_ascii=False)
    print("[*] Το τελικό mapping αποθηκεύτηκε στο 'jelly_to_cfunc_mapping.json'")

if __name__ == '__main__':
    run_fuzzy_matching()