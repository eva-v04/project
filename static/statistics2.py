import json
import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def find_reachable(jelly_json):
    # μετατροπή του fun2fun σε γραφο
    adj = {}
    for caller, callee in jelly_json['fun2fun']:
        caller, callee = str(caller), str(callee) # Σιγουριά να είναι strings
        if caller not in adj:
            adj[caller] = []
        adj[caller].append(callee)
    
    # βρίσκουμε αρχικές συναρτήσεις από τα entries
    entry_files = set(jelly_json['entries'])
    roots = []
    for fid, location in jelly_json['functions'].items():
        file_idx = int(location.split(':')[0])
        if jelly_json['files'][file_idx] in entry_files:
            roots.append(str(fid))

    print(f"DEBUG: Entry files found: {jelly_json['entries']}")
    print(f"DEBUG: Root functions (start nodes): {roots}")

    # DFS
    reachable = set()
    stack = roots
    while stack:
        current = stack.pop()
        if current not in reachable:
            reachable.add(current)
            # Προσθέτουμε γείτονες χρησιμοποιώντας τον γραφο adj
            if current in adj:
                print(f"DEBUG: Visiting {current}, adding neighbors: {adj[current]}")
                stack.extend(adj[current])
            
    return reachable

def calculate_detailed_statistics(jelly_json, reachable_fids):
    all_files = jelly_json['files']
    reachable_files_indices = set()
    
    # Στατιστικά Συναρτήσεων
    total_functions = len(jelly_json['functions'])
    reachable_functions_count = len(reachable_fids)

    # Στατιστικά Αρχείων
    for fid in reachable_fids:
        location = jelly_json['functions'][str(fid)]
        file_idx = int(location.split(':')[0])
        reachable_files_indices.add(file_idx)
    
    total_files = len(all_files)
    reachable_files_count = len(reachable_files_indices)

    # Στατιστικά Πακέτων
    all_packages = set()
    reachable_packages = set()

    for idx, file_path in enumerate(all_files):
        # Πιο σωστή εξαγωγή πακέτου
        parts = file_path.split('/')
        package_name = parts[0] if len(parts) > 1 else "root"
        
        all_packages.add(package_name)
        if idx in reachable_files_indices:
            reachable_packages.add(package_name)

    print(f"DEBUG: Total functions: {total_functions}, Reachable functions: {reachable_functions_count}")
    print(f"DEBUG: Total files: {total_files}, Reachable files: {reachable_files_count}")
    print(f"DEBUG: Total packages: {len(all_packages)}, Reachable packages: {len(reachable_packages)}")

    return {
        "functions": {"total": total_functions, "reachable": reachable_functions_count},
        "files": {"total": total_files, "reachable": reachable_files_count},
        "packages": {"total": len(all_packages), "reachable": len(reachable_packages)}
    }

#εκτέλεση
with open('static/analysis_sharp_0.34.3/sharp.json', 'r') as f:
    data = json.load(f)

reachable_ids = find_reachable(data)

results = calculate_detailed_statistics(data, reachable_ids)

print("\n--- FINAL RESULTS ---")
print(results)