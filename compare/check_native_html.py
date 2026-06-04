import json
import os
import re

def load_json(filepath):
    if not os.path.exists(filepath):
        print(f" Το αρχείο {filepath} δεν βρέθηκε.")
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_json_from_html(html_filepath):
    """
    Ανοίγει το HTML αρχείο και εξάγει το JSON γράφημα που έκανε inject το Jelly.
    """
    if not os.path.exists(html_filepath):
        print(f"Το αρχείο {html_filepath} δεν βρέθηκε.")
        return None
        
    with open(html_filepath, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Αναζήτηση της δομής JSON των δεδομένων μέσα στο script block του HTML
    match = re.search(r'\{\s*"graphs"\s*:\s*\[.*\]\s*\}', html_content, re.DOTALL)
    if not match:
        print("Δεν βρέθηκαν δεδομένα γραφήματος μέσα στο HTML αρχείο.")
        return None
        
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as e:
        print(f"Σφάλμα  {e}")
        return None

def check_native_nodes_in_html():
    api_results = load_json('api_results.json')
    html_data = extract_json_from_html('sqlite3-withflags.html')
    
    if not (api_results and html_data):
        return

    # Συγκέντρωση όλων των function nodes από το HTML γράφημα
    all_html_nodes = []
    for graph in html_data.get("graphs", []):
        for element in graph.get("elements", []):
            data = element.get("data", {})
            if data.get("kind") == "function":
                all_html_nodes.append(data)

    print("=" * 70)
    print("ΕΛΕΓΧΟΣ ΟΠΤΙΚΟΠΟΙΕΙΣΗΣ NATIVE NODES ΣΤΟ HTML (CALL GRAPH)")
    print("=" * 70)

    total_checked = 0
    total_found = 0
    total_missing = 0

    # Πλοήγηση στο api_results.json ανά κατηγορία (call, read, write κλπ.)
    for category, patterns in api_results.items():
        for pattern_name, edges in patterns.items():
            
            # Καθαρίζουμε το pattern_name αν περιέχει ειδικούς χαρακτήρες για ευκολότερο substring matching
            clean_pattern_name = pattern_name.strip()
            
            print(f"\n🔹 Έλεγχος Pattern API: '{clean_pattern_name}'")
            print("-" * 60)
            
            for edge in edges:
                callee_info = edge.get("callee", {})
                callee_coords = callee_info.get("name") # π.χ. "82:4:82:53"
                
                if not callee_coords:
                    continue
                
                total_checked += 1
                caller_info = edge.get("caller")
                caller_desc = f"Συνάρτηση {caller_info['name']}" if caller_info else "Top-level Code"
                
                found_in_html = False
                matched_node_display_name = ""
                
                # ελεγχος αν το όνομα του pattern αντιστοιχεί σε κάποιο Node του HTML
                for node in all_html_nodes:
                    node_name = node.get("name", "")          # π.χ. "[Native API] native:sqlite3..."
                    node_fullname = node.get("fullName", "")  # π.χ. "Native Call: native:sqlite3..."
                    
                    # το Jelly ονομάζει τα native nodes χρησιμοποιώντας το pattern_name 
                    # ελέγχουμε αν το καθαρό pattern name περιέχεται στο όνομα του node
                    if clean_pattern_name in node_name or clean_pattern_name in node_fullname:
                        found_in_html = True
                        matched_node_display_name = node_name
                        break
                
                if found_in_html:
                    print(f"ΟΠΤΙΚΟΠΟΙΕΙΤΑΙ: '{callee_coords}' -> Βρέθηκε ως '{matched_node_display_name}'")
                    print(f"   └─ Caller: {caller_desc} | Αρχείο: {callee_info.get('loc')}")
                    total_found += 1
                else:
                    print(f"ΛΕΙΠΕΙ ΑΠΟ ΤΟ HTML: '{callee_coords}' (Pattern: {clean_pattern_name})")
                    print(f"   └─ Caller: {caller_desc} | Αρχείο: {callee_info.get('loc')}")
                    total_missing += 1

    print("\n" + "=" * 70)
    print("ΤΕΛΙΚΟ ΑΠΟΤΕΛΕΣΜΑ (HTML VISUALIZATION)")
    print("=" * 70)
    print(f"• Συνολικά Native Nodes που ελέγχθηκαν: {total_checked}")
    print(f"• Nodes που σχεδιάζονται στο HTML:     {total_found}")
    print(f"• Nodes που λείπουν από το HTML:       {total_missing}")
    if total_checked > 0:
        success_rate = (total_found / total_checked) * 100
        print(f"• Ποσοστό Επιτυχίας Οπτικοποίησης:     {success_rate:.2f}%")
    print("=" * 70)

if __name__ == "__main__":
    check_native_nodes_in_html()