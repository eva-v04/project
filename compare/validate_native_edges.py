import json
import os

def validate_native_diff():
    api_file = "api_results.json"
    old_jelly_file = "sqlite3-noflags.json"
    new_jelly_file = "sqlite3-withflags.json"
    
    
    with open(api_file, 'r', encoding='utf-8') as f:
        api_data = json.load(f)
    with open(old_jelly_file, 'r', encoding='utf-8') as f:
        old_data = json.load(f)
    with open(new_jelly_file, 'r', encoding='utf-8') as f:
        new_data = json.load(f)

    total_expected_calls = 0
    api_native_files = set()
    for cat, sub in api_data.items():
        if isinstance(sub, dict):
            for api_name, occs in sub.items():
                for occ in occs:
                    fname = os.path.basename(occ.get("filename", ""))
                    api_native_files.add(fname)
                    total_expected_calls += len(occ.get("callers", []))
                    
    print(f"[+] Αναμενόμενες Native Κλήσεις (από api_results): {total_expected_calls}")

    # Συναρτήσεις βοήθειας για μετατροπή IDs σε Location Strings
    def get_graph_edges_as_strings(graph_json):
        files = graph_json.get("files", [])
        functions = graph_json.get("functions", {})
        
        def id_to_loc(node_id):
            node_id = str(node_id)
            if node_id not in functions:
                return f"UnknownNode_{node_id}"
            f_str = functions[node_id]
            parts = f_str.split(":")
            if len(parts) == 5: # Δικό μας custom native string (fileIdx:line:col:line:col)
                f_idx = parts[0]
                if int(f_idx) < len(files):
                    filename = os.path.basename(files[int(f_idx)])
                    return f"NATIVE:{filename}:{parts[1]}:{parts[2]}"
            return f_str # Επιστρέφει το κανονικό JS function string

        # Μαζεύουμε fun2fun και call2fun
        edges_set = set()
        for edge in graph_json.get("fun2fun", []):
            edges_set.add((id_to_loc(edge[0]), id_to_loc(edge[1])))
        for edge in graph_json.get("call2fun", []):
            edges_set.add((id_to_loc(edge[0]), id_to_loc(edge[1])))
        return edges_set

    old_edges = get_graph_edges_as_strings(old_data)
    
    new_edges = get_graph_edges_as_strings(new_data)

    purely_new_edges = new_edges - old_edges
    print(f"[+] Βρέθηκαν {len(purely_new_edges)} συνολικά νέες ακμές στο text-level diff.")

    new_native_edges = []
    for src, dst in purely_new_edges:
        if dst.startswith("NATIVE:") or src.startswith("NATIVE:"):
            new_native_edges.append((src, dst))

    total_actual_new_native = len(new_native_edges)

    print("\n" + "-"*50)
    print(f"[*] Native ακμές (που ΔΕΝ υπήρχαν στο παλιό): {total_actual_new_native}")
    print("-"*50)

if __name__ == "__main__":
    validate_native_diff()