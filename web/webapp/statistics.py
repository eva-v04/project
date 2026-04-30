import json
import os
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')
import io
import base64


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def generate_full_stats(pkg, ver):
    analysis_folder = os.path.join(BASE_DIR, 'static', f"analysis_{pkg}_{ver}")
#    lock_path = os.path.join(analysis_folder, "package-lock.json")
    jelly_path = os.path.join(analysis_folder, f"{pkg}.json")

    if not os.path.exists(analysis_folder):
        print(f"Error: Folder {analysis_folder} not found!")
        return None
    
    with open(jelly_path, 'r') as f:
        jelly_json = json.load(f)

    # Καλούμε τη νέα σου λογική (από το statistics2.py)
    reachable_fids = find_reachable(jelly_json)
    detailed_stats = calculate_detailed_statistics(jelly_json, reachable_fids)

    # Επιστρέφουμε τα δεδομένα στη μορφή που τα θέλει το views.py
    return {
        'function_stats': {
            'total_functions': detailed_stats['functions']['total'],
            'reachable_functions': detailed_stats['functions']['reachable'],
            'percent': detailed_stats['functions']['percentage']  # <--- ΠΡΟΣΘΗΚΗ
        },
        'file_stats': {
            'total_files': detailed_stats['files']['total'],
            'reachable_files': detailed_stats['files']['reachable'],
            'percent': detailed_stats['files']['percentage']      # <--- ΠΡΟΣΘΗΚΗ
        },
        'package_stats': {
            'total_packages': detailed_stats['packages']['total'],
            'reachable_packages': detailed_stats['packages']['reachable'],
            'percent': detailed_stats['packages']['percentage']  # <--- ΠΡΟΣΘΗΚΗ
        }
    }



def get_matplotlib_graph(reachable, total):

    plt.clf() # Καθαρίζει το προηγούμενο γράφημα
    if total == 0: return ""

    # Δεδομένα
    labels = ['Used', 'Unused']
    sizes = [reachable, total - reachable]
    colors = ['#00d2ff', '#1e293b']

    # Δημιουργία Plot
    fig, ax = plt.subplots(figsize=(5, 4), facecolor='none')
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors, textprops={'color':"blue"})
    
    # Μετατροπή σε εικόνα στη μνήμη
    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True)
    buf.seek(0)
    
    # Μετατροπή σε Base64 string
    string = base64.b64encode(buf.read())
    uri = string.decode('utf-8')
    plt.close(fig)
    return uri


def get_matplotlib_bar_graph(reachable, total):
    plt.clf()
    if total == 0: return ""
    
    unused = total - reachable
    labels = ['Used', 'Unused']
    values = [reachable, unused]
    
    fig, ax = plt.subplots(figsize=(5, 4), facecolor='none')
    bars = ax.bar(labels, values, color=['#38bdf8', '#1e293b'])
    
    # Ρυθμίσεις για να φαίνεται όμορφα στο UI
    ax.set_facecolor('none')
    ax.tick_params(colors='blue')
    for spine in ax.spines.values():
        spine.set_edgecolor('blue')
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


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

    #print(f"DEBUG: Entry files found: {jelly_json['entries']}")
    #print(f"DEBUG: Root functions (start nodes): {roots}")

    # DFS
    reachable = set()
    stack = roots
    while stack:
        current = stack.pop()
        if current not in reachable:
            reachable.add(current)
            # Προσθέτουμε γείτονες χρησιμοποιώντας τον γραφο adj
            if current in adj:
     #           print(f"DEBUG: Visiting {current}, adding neighbors: {adj[current]}")
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

    # Υπολογισμός ποσοστών 
    func_perc = (reachable_functions_count / total_functions * 100) if total_functions > 0 else 0
    file_perc = (reachable_files_count / total_files * 100) if total_files > 0 else 0
    pkg_perc = (len(reachable_packages) / len(all_packages) * 100) if len(all_packages) > 0 else 0

    #print(f"DEBUG: Total functions: {total_functions}, Reachable functions: {reachable_functions_count}")
    #print(f"DEBUG: Total files: {total_files}, Reachable files: {reachable_files_count}")
    #print(f"DEBUG: Total packages: {len(all_packages)}, Reachable packages: {len(reachable_packages)}")

    return {
        "functions": {
            "total": total_functions, 
            "reachable": reachable_functions_count, 
            "percentage": round(func_perc, 2)
        },
        "files": {
            "total": total_files, 
            "reachable": reachable_files_count, 
            "percentage": round(file_perc, 2)
        },
        "packages": {
            "total": len(all_packages), 
            "reachable": len(reachable_packages), 
            "percentage": round(pkg_perc, 2)
        }
    }