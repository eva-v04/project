import json
import os
from collections import Counter

def load_json(filepath):
    if not os.path.exists(filepath):
        print(f"❌ Σφάλμα: Το αρχείο {filepath} δεν βρέθηκε.")
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def analyze_api_results():
    api_results = load_json('api_results.json')
    if not api_results:
        return

    print("=" * 75)
    print("📊 ΣΤΑΤΙΣΤΙΚΗ ΑΝΑΛΥΣΗ ΚΑΙ ΕΝΤΟΠΙΣΜΟΣ ΔΙΠΛΟΤΥΠΩΝ ΣΤΟ API_RESULTS.JSON")
    print("=" * 75)

    # Λίστες για τη συλλογή των στοιχείων
    all_callee_names = []
    all_callee_locs = []
    
    # Μετρητής για το σύνολο των εγγραφών
    total_edges = 0

    # Διατρέχουμε όλες τις κατηγορίες (κυρίως "call")
    for pattern_type, patterns in api_results.items():
        if pattern_type != "call":
            continue
            
        for pattern_name, edges in patterns.items():
            for edge in edges:
                total_edges += 1
                callee_info = edge.get("callee", {})
                
                # 1. Συλλογή Callee Names (π.χ. "82:4:82:53")
                c_name = callee_info.get("name")
                if c_name:
                    all_callee_names.append(c_name)
                
                # 2. Συλλογή Πλήρων Τοποθεσιών (κλειδί το loc string μαζί με το path)
                c_loc = callee_info.get("loc")
                if c_loc:
                    all_callee_locs.append(c_loc)

    # Υπολογισμός συχνοτήτων εμφάνισης με το Counter
    name_counts = Counter(all_callee_names)
    loc_counts = Counter(all_callee_locs)

    # Φιλτράρισμα για να κρατήσουμε ΜΟΝΟ όσα εμφανίζονται πάνω από 1 φορά (επαναλήψεις)
    duplicate_names = {name: count for name, count in name_counts.items() if count > 1}
    duplicate_locs = {loc: count for loc, count in loc_counts.items() if count > 1}

    print(f"• Συνολικές καταγεγραμμένες native ακμές: {total_edges}")
    print(f"• Μοναδικά Callee Names που εντοπίστηκαν: {len(name_counts)}")
    print(f"• Μοναδικές Τοποθεσίες (Locations):      {len(loc_counts)}")
    print("-" * 75)

    # --- ΕΝΟΤΗΤΑ 1: ΕΠΑΝΕΜΦΑΝΙΣΗ CALLEE NAMES ---
    print(f"\n🔄 1. ΕΠΑΝΕΜΦΑΝΙΖΟΜΕΝΑ CALLEE NAMES ({len(duplicate_names)} στοιχεία)")
    print("-" * 75)
    if not duplicate_names:
        print("  ✅ Κανένα Callee Name δεν επανεμφανίζεται! Όλα είναι μοναδικά.")
    else:
        # Ταξινόμηση από το μεγαλύτερο count στο μικρότερο
        sorted_names = sorted(duplicate_names.items(), key=lambda x: x[1], reverse=True)
        print(f"{'Callee Name (Coordinates)':<30} | {'Φορές Επανεμφάνισης':<20}")
        print("-" * 75)
        for name, count in sorted_names:
            print(f"{name:<30} | {count} φορές")

    # --- ΕΝΟΤΗΤΑ 2: ΕΠΑΝΕΜΦΑΝΙΣΗ ΤΟΠΟΘΕΣΙΩΝ (LOCATIONS) ---
    print(f"\n📍 2. ΕΠΑΝΕΜΦΑΝΙΖΟΜΕΝΕΣ ΤΟΠΟΘΕΣΙΕΣ/LOCATIONS ({len(duplicate_locs)} στοιχεία)")
    print("-" * 75)
    if not duplicate_locs:
        print("  ✅ Καμία τοποθεσία (Full Location Path) δεν επανεμφανίζεται!")
    else:
        # Ταξινόμηση από το μεγαλύτερο count στο μικρότερο
        sorted_locs = sorted(duplicate_locs.items(), key=lambda x: x[1], reverse=True)
        print(f"{'Πλήρης Τοποθεσία (Location)':<55} | {'Φορές':<10}")
        print("-" * 75)
        for loc, count in sorted_locs:
            # Αν το path είναι πολύ μεγάλο, κρατάμε τα τελευταία 50 string chars για να μην χαλάει η στοίχιση
            display_loc = loc if len(loc) <= 55 else "..." + loc[-52:]
            print(f"{display_loc:<55} | {count} φορές")

    print("=" * 75)

if __name__ == "__main__":
    analyze_api_results()