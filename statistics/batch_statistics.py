import json
import os
import sys
import re

def find_reachable_from_root(jelly_json, root_package_name):
    """
    Εκτελεί DFS στον γράφο κλήσεων (fun2fun) ξεκινώντας ΑΠΟΚΛΕΙΣΤΙΚΑ 
    από τα entries του αρχικού πακέτου.
    """
    adj = {}
    for caller, callee in jelly_json.get('fun2fun', []):
        caller, callee = str(caller), str(callee)
        if caller not in adj:
            adj[caller] = []
        adj[caller].append(callee)

    entry_files = set(jelly_json.get('entries', []))
    files = jelly_json.get('files', [])
    functions = jelly_json.get('functions', {})

    root_entries = {f for f in entry_files if f.startswith(f"{root_package_name}/") or f == root_package_name}

    roots = []
    for fid, location in functions.items():
        if isinstance(location, str) and ':' in location and not location.startswith("[Native]"):
            file_idx_str = location.split(':')[0]
            if file_idx_str.isdigit():
                file_idx = int(file_idx_str)
                if file_idx < len(files) and files[file_idx] in root_entries:
                    roots.append(str(fid))

    reachable = set()
    stack = roots
    while stack:
        current = stack.pop()
        if current not in reachable:
            reachable.add(current)
            if current in adj:
                stack.extend(adj[current])

    return reachable


def get_ground_truth_native_functions(ghidra_json_path):
    """
    Διαβάζει το πλήρες αρχείο Ghidra Symbol Export για να βρει
    ΟΛΕΣ τις C/C++ συναρτήσεις που υπάρχουν στο compiled binary.
    """
    if not os.path.exists(ghidra_json_path):
        return 0
    try:
        with open(ghidra_json_path, 'r', encoding='utf-8') as f:
            ghidra_data = json.load(f)
            nodes = ghidra_data.get("nodes", [])
            if isinstance(nodes, list):
                return len(nodes)
            elif isinstance(nodes, dict):
                return len(nodes.keys())
    except Exception as e:
        print(f"φάλμα κατά την ανάγνωση του Ghidra file: {e}")
    return 0 #νέα δυνάρτηση για να περιέχονται συναρτήσεις των dependencies


def get_ground_truth_packages(package_lock_path):
    installed_packages = set()
    if not os.path.exists(package_lock_path):
        return installed_packages

    try:
        with open(package_lock_path, 'r', encoding='utf-8') as f:
            lock_data = json.load(f)
        
        if "packages" in lock_data:
            for pkg_path in lock_data["packages"].keys():
                if pkg_path:
                    clean_name = pkg_path.replace("node_modules/", "")
                    if clean_name:
                        installed_packages.add(clean_name)
        elif "dependencies" in lock_data:
            installed_packages.update(lock_data["dependencies"].keys())
    except Exception as e:
        print(f" Σφάλμα κατά την ανάγνωση του {package_lock_path}: {e}")

    return installed_packages


def get_ground_truth_files_and_functions(node_modules_path):
    all_disk_files = []
    total_disk_functions = 0

    func_pattern = re.compile(
        r'(?:function\s*\w*\s*\(|(?:\b(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)|(?:\b\w+\s*\([^)]*\)\s*\{))'
    )

    if not os.path.exists(node_modules_path):
        return all_disk_files, total_disk_functions

    for root, _, files in os.walk(node_modules_path):
        for file in files:
            if file.endswith('.js') or file.endswith('.cjs') or file.endswith('.mjs'):
                full_path = os.path.join(root, file)
                all_disk_files.append(full_path)
                
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        matches = func_pattern.findall(content)
                        total_disk_functions += len(matches)
                except Exception:
                    pass

    return all_disk_files, total_disk_functions


def analyze_package_reachability(jelly_json, root_pkg_name, node_modules_dir="node_modules", package_lock_file="package-lock.json"):
    jelly_files = jelly_json.get('files', [])
    functions = jelly_json.get('functions', {})
    calls = jelly_json.get('calls', {})
    fun2fun = jelly_json.get('fun2fun', [])
    call2fun = jelly_json.get('call2fun', [])
    
    reachable_fids = find_reachable_from_root(jelly_json, root_pkg_name)

    # Κατηγοριοποίηση (JS, Gasket, Ghidra)
    js_reachable = set()
    gasket_reachable, gasket_total = set(), set()
    ghidra_reachable, ghidra_total = set(), set()
    reachable_file_indices = set()

    for fid, loc in functions.items():
        fid_str = str(fid)
        loc_str = str(loc)

        if loc_str.startswith("[Native]"):
            if "[C Function Gasket]" in loc_str:
                gasket_total.add(fid_str)
                if fid_str in reachable_fids:
                    gasket_reachable.add(fid_str)
            elif "[C Function Ghidra]" in loc_str:
                ghidra_total.add(fid_str)
                if fid_str in reachable_fids:
                    ghidra_reachable.add(fid_str)
        else:
            if fid_str in reachable_fids:
                js_reachable.add(fid_str)
                if ':' in loc_str:
                    f_idx = loc_str.split(':')[0]
                    if f_idx.isdigit():
                        reachable_file_indices.add(int(f_idx))

    # --- Call Site & Call Graph Metrics ---
    call_to_callees = {}
    for call_id, callee_id in call2fun:
        call_id_str, callee_id_str = str(call_id), str(callee_id)
        if call_id_str not in call_to_callees:
            call_to_callees[call_id_str] = []
        call_to_callees[call_id_str].append(callee_id_str)

    total_call_sites = len(calls)
    zero_or_one_callee = 0
    multiple_callees = 0
    native_or_ext_callees = 0

    for call_id in calls.keys():
        call_id_str = str(call_id)
        callees = call_to_callees.get(call_id_str, [])
        num_callees = len(callees)

        if num_callees <= 1:
            zero_or_one_callee += 1
        else:
            multiple_callees += 1

        has_native = any(str(functions.get(cid, '')).startswith("[Native]") for cid in callees)
        if has_native:
            native_or_ext_callees += 1

    all_callees_in_graph = set()
    for _, callee in fun2fun:
        all_callees_in_graph.add(str(callee))
    for _, callee in call2fun:
        all_callees_in_graph.add(str(callee))

    zero_caller_functions = [fid for fid in functions.keys() if str(fid) not in all_callees_in_graph]

    # Ground Truth Metrics
    ground_truth_pkgs = get_ground_truth_packages(package_lock_file)
    jelly_reachable_pkgs = set()

    for idx in reachable_file_indices:
        if idx < len(jelly_files):
            fpath = jelly_files[idx]
            parts = fpath.split('/')
            pkg = f"{parts[0]}/{parts[1]}" if parts[0].startswith('@') and len(parts) > 1 else parts[0]
            jelly_reachable_pkgs.add(pkg)

    total_packages_gt = len(ground_truth_pkgs) if ground_truth_pkgs else len(jelly_reachable_pkgs)
    all_disk_files, total_disk_functions = get_ground_truth_files_and_functions(node_modules_dir)
    
    reachable_jelly_filepaths = [jelly_files[i] for i in reachable_file_indices if i < len(jelly_files)]
    matched_reachable_files = set()
    for disk_file in all_disk_files:
        normalized_disk_path = disk_file.replace('\\', '/')
        for j_file in reachable_jelly_filepaths:
            if normalized_disk_path.endswith(j_file):
                matched_reachable_files.add(disk_file)
                break

    total_files_gt = len(all_disk_files) if all_disk_files else len(jelly_files)
    reachable_files_cnt = len(matched_reachable_files) if all_disk_files else len(reachable_file_indices)
    total_js_functions_gt = total_disk_functions if total_disk_functions > 0 else len([f for f in functions.values() if not str(f).startswith("[Native]")])




    ghidra_dir = os.path.join("..", "web", "static")
    pkg_ghidra_name = "lz4-napi" if root_pkg_name == "lz4" else root_pkg_name
    ghidra_file = os.path.join(ghidra_dir, f"ghidra_{pkg_ghidra_name}.json")
    
    native_gt_from_file = get_ground_truth_native_functions(ghidra_file)

    if native_gt_from_file > 0:
        total_native = native_gt_from_file
        total_ghidra_gt = native_gt_from_file - len(gasket_total) 
    else:
        total_native = len(gasket_total) + len(ghidra_total)
        total_ghidra_gt = len(ghidra_total)

    reachable_native = len(gasket_reachable) + len(ghidra_reachable)

    combined_total_functions = total_js_functions_gt + total_native
    combined_reachable_functions = len(js_reachable) + reachable_native

    def calc_cov(reach, tot):
        return round((reach / tot * 100), 2) if tot > 0 else 0.0

    return {
        "package": root_pkg_name,
        "call_graph_metrics": {
            "fun2fun_edges": len(fun2fun),
            "call2fun_edges": len(call2fun),
            "total_call_sites": total_call_sites,
            "zero_or_one_callee": {
                "count": zero_or_one_callee,
                "pct": calc_cov(zero_or_one_callee, total_call_sites)
            },
            "multiple_callees": {
                "count": multiple_callees,
                "pct": calc_cov(multiple_callees, total_call_sites)
            },
            "native_or_external_callees": {
                "count": native_or_ext_callees,
                "pct": calc_cov(native_or_ext_callees, total_call_sites)
            },
            "zero_caller_functions": {
                "count": len(zero_caller_functions),
                "pct": calc_cov(len(zero_caller_functions), len(functions))
            }
        },
        "packages": {
            "ground_truth_total": total_packages_gt,
            "reachable": len(jelly_reachable_pkgs),
            "coverage_pct": calc_cov(len(jelly_reachable_pkgs), total_packages_gt),
            "list_reachable": sorted(list(jelly_reachable_pkgs))
        },
        "files": {
            "ground_truth_total": total_files_gt,
            "reachable": reachable_files_cnt,
            "coverage_pct": calc_cov(reachable_files_cnt, total_files_gt)
        },
        "functions": {
            "combined_total": {
                "total": combined_total_functions,
                "reachable": combined_reachable_functions,
                "coverage_pct": calc_cov(combined_reachable_functions, combined_total_functions)
            },
            "js_functions": {
                "ground_truth_total": total_js_functions_gt,
                "reachable": len(js_reachable),
                "coverage_pct": calc_cov(len(js_reachable), total_js_functions_gt)
            },
            "native_summary": {
                "total": total_native,
                "reachable": reachable_native,
                "coverage_pct": calc_cov(reachable_native, total_native)
            },
            "native_gasket": {
                "total": len(gasket_total),
                "reachable": len(gasket_reachable),
                "coverage_pct": calc_cov(len(gasket_reachable), len(gasket_total))
            },
            "native_ghidra": {
                "total": total_ghidra_gt,
                "reachable": len(ghidra_reachable),
                "coverage_pct": calc_cov(len(ghidra_reachable), total_ghidra_gt)
            }
        }
    }


def print_formatted_results(stats):
    print(f" REACHABILITY & CALL GRAPH ANALYSIS FOR: {stats['package']}")
    
    # Structural Reachability Table
    print(f"│ {'Level / Category':<24} │ {'Ground Truth':<12} │ {'Reachable':<12} │ {'Coverage %':<10} │")
    print("├" + "─" * 26 + "┼" + "─" * 14 + "┼" + "─" * 14 + "┼" + "─" * 12 + "┤")
    print(f"│ 1. Packages (Dependencies)│ {stats['packages']['ground_truth_total']:<12} │ {stats['packages']['reachable']:<12} │ {stats['packages']['coverage_pct']:>8.1f}%   │")
    print(f"│ 2. Files (node_modules)   │ {stats['files']['ground_truth_total']:<12} │ {stats['files']['reachable']:<12} │ {stats['files']['coverage_pct']:>8.1f}%   │")
    
    cmb_f = stats['functions']['combined_total']
    js_f = stats['functions']['js_functions']
    print(f"│ 3. Combined Total Functions│ {cmb_f['total']:<12} │ {cmb_f['reachable']:<12} │ {cmb_f['coverage_pct']:>8.1f}%   │")
    print(f"│  ├─ JS Functions (Regex)  │ {js_f['ground_truth_total']:<12} │ {js_f['reachable']:<12} │ {js_f['coverage_pct']:>8.1f}%   │")

    print("├" + "─" * 26 + "┼" + "─" * 14 + "┼" + "─" * 14 + "┼" + "─" * 12 + "┤")
    nat_sum = stats['functions']['native_summary']
    gsk = stats['functions']['native_gasket']
    ghd = stats['functions']['native_ghidra']
    print(f"│  ├─ All Native Code       │ {nat_sum['total']:<12} │ {nat_sum['reachable']:<12} │ {nat_sum['coverage_pct']:>8.1f}%   │")
    print(f"│  │   ├─ Gasket Native     │ {gsk['total']:<12} │ {gsk['reachable']:<12} │ {gsk['coverage_pct']:>8.1f}%   │")
    print(f"│  │   └─ Ghidra Native     │ {ghd['total']:<12} │ {ghd['reachable']:<12} │ {ghd['coverage_pct']:>8.1f}%   │")
    print("└" + "─" * 26 + "┴" + "─" * 14 + "┴" + "─" * 14 + "┴" + "─" * 12 + "┘")

    # 2. Call Graph Metrics Block
    cg = stats["call_graph_metrics"]
    print("\nCALL GRAPH TOPOLOGY & RESOLUTION:")
    print(f"  • Call Edges:  fun->fun: {cg['fun2fun_edges']}  |  call->fun: {cg['call2fun_edges']}")
    print(f"  • Call Sites Breakdown (Total: {cg['total_call_sites']}):")
    print(f"     - Zero or One Callee : {cg['zero_or_one_callee']['count']} ({cg['zero_or_one_callee']['pct']}%)")
    print(f"     - Multiple Callees   : {cg['multiple_callees']['count']} ({cg['multiple_callees']['pct']}%)")
    print(f"     - Native / External  : {cg['native_or_external_callees']['count']} ({cg['native_or_external_callees']['pct']}%)")
    print(f"  • Functions with Zero Callers: {cg['zero_caller_functions']['count']} ({cg['zero_caller_functions']['pct']}%)\n")


#εκτλελεση
if __name__ == "__main__":
    OUTPUT_FILE = "analysis_summary.json"
    all_results = []

    if len(sys.argv) > 1:
        json_files = sys.argv[1:]
        for filepath in json_files:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                pkg_name = os.path.basename(filepath).replace('.json', '').replace('-withflags', '')  #επειδή τα json έχουν μορφή: <package_name>-withflags.json
                results = analyze_package_reachability(data, root_pkg_name=pkg_name)
                
                print_formatted_results(results)
                all_results.append(results)

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)

        print(f"Τα στατιστικά αποθηκεύτηκαν στο: '{OUTPUT_FILE}'")
    else:
        print("error")
