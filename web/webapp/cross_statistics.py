import json
import os
import io
import base64
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from django.conf import settings


def find_reachable_from_root(jelly_json, root_package_name):
    # Κατασκευή γράφου γειτνίασης (adj)
    adj = {}
    
    # 1. Fun2Fun Edges
    for caller, callee in jelly_json.get('fun2fun', []):
        caller, callee = str(caller), str(callee)
        adj.setdefault(caller, []).append(callee)

    # 2. Call2Fun Resolution
    functions = jelly_json.get('functions', {})
    calls = jelly_json.get('calls', {})
    call2fun = jelly_json.get('call2fun', [])

    call_to_caller_fn = {}
    for fid, loc in functions.items():
        if isinstance(loc, str) and ':' in loc and not loc.startswith("[Native]"):
            f_parts = loc.split(':')
            if len(f_parts) >= 5:
                f_idx, f_sl, f_el = int(f_parts[0]), int(f_parts[1]), int(f_parts[3])
                for cid, cloc in calls.items():
                    c_parts = cloc.split(':')
                    if len(c_parts) >= 4 and int(c_parts[0]) == f_idx:
                        c_sl = int(c_parts[1])
                        if f_sl <= c_sl <= f_el:
                            call_to_caller_fn[str(cid)] = str(fid)

    for cid, callee in call2fun:
        caller_fn = call_to_caller_fn.get(str(cid))
        if caller_fn:
            adj.setdefault(caller_fn, []).append(str(callee))

    entry_files = set(jelly_json.get('entries', []))
    files = jelly_json.get('files', [])

    # Εύρεση ριζών ακριβώς όπως στο Jelly: όλες οι συναρτήσεις των entry files
    roots = []
    for fid, location in functions.items():
        if isinstance(location, str) and ':' in location and not location.startswith("[Native]"):
            file_idx_str = location.split(':')[0]
            if file_idx_str.isdigit():
                file_idx = int(file_idx_str)
                if file_idx < len(files) and files[file_idx] in entry_files:
                    roots.append(str(fid))

    reachable = set()
    stack = list(roots)
    while stack:
        current = stack.pop()
        if current not in reachable:
            reachable.add(current)
            if current in adj:
                stack.extend(adj[current])

    return reachable


def get_ground_truth_native_functions(ghidra_json_path):
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
    except Exception:
        pass
    return 0


def analyze_package_reachability(jelly_json, root_pkg_name):
    jelly_files = jelly_json.get('files', [])
    functions = jelly_json.get('functions', {})
    calls = jelly_json.get('calls', {})
    fun2fun = jelly_json.get('fun2fun', [])
    call2fun = jelly_json.get('call2fun', [])
    
    reachable_fids = find_reachable_from_root(jelly_json, root_pkg_name)

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
                    f_int = int(f_idx)
                    if fid_str in reachable_fids:
                        reachable_file_indices.add(f_int)

    # Υπολογισμός Πακέτων & Αρχείων ΑΠΟΚΛΕΙΣΤΙΚΑ από το Runtime Scope του Jelly
    all_packages = set()
    reachable_packages = set()

    for idx, file_path in enumerate(jelly_files):
        # Κανονικοποίηση πακέτου: αν είναι scoped (π.χ. @img/sharp) κρατάμε τα 2 μέρη
        parts = file_path.split('/')
        pkg_name = f"{parts[0]}/{parts[1]}" if parts[0].startswith('@') and len(parts) > 1 else parts[0]
        
        all_packages.add(pkg_name)
        if idx in reachable_file_indices:
            reachable_packages.add(pkg_name)

    total_packages = len(all_packages)
    reachable_packages_count = len(reachable_packages)

    total_files = len(jelly_files)
    reachable_files_count = len(reachable_file_indices)

    # JS Functions
    total_js_functions = len([f for f in functions.values() if not str(f).startswith("[Native]")])
    reachable_js_functions = len(js_reachable)

    # Native Functions από Ghidra JSON
    ghidra_file = os.path.join(settings.BASE_DIR, "static", f"ghidra_{root_pkg_name}.json")
    native_gt_from_file = get_ground_truth_native_functions(ghidra_file)

    if native_gt_from_file > 0:
        total_native = native_gt_from_file
        total_ghidra_gt = max(0, native_gt_from_file - len(gasket_total))
    else:
        total_native = len(gasket_total) + len(ghidra_total)
        total_ghidra_gt = len(ghidra_total)

    reachable_native = len(gasket_reachable) + len(ghidra_reachable)
    combined_total_functions = total_js_functions + total_native
    combined_reachable_functions = reachable_js_functions + reachable_native

    # Call metrics
    call_to_callees = {}
    for call_id, callee_id in call2fun:
        call_to_callees.setdefault(str(call_id), []).append(str(callee_id))

    total_call_sites = len(calls)
    zero_or_one_callee = 0
    multiple_callees = 0
    native_or_ext_callees = 0

    for call_id in calls.keys():
        callees = call_to_callees.get(str(call_id), [])
        if len(callees) <= 1:
            zero_or_one_callee += 1
        else:
            multiple_callees += 1

        if any(str(functions.get(cid, '')).startswith("[Native]") for cid in callees):
            native_or_ext_callees += 1

    all_callees_in_graph = {str(c) for _, c in fun2fun} | {str(c) for _, c in call2fun}
    zero_caller_functions = [fid for fid in functions.keys() if str(fid) not in all_callees_in_graph]

    def calc_cov(reach, tot):
        return round((reach / tot * 100), 2) if tot > 0 else 0.0

    return {
        "package": root_pkg_name,
        "call_graph_metrics": {
            "fun2fun_edges": len(fun2fun),
            "call2fun_edges": len(call2fun),
            "total_call_sites": total_call_sites,
            "zero_or_one_callee": {"count": zero_or_one_callee, "pct": calc_cov(zero_or_one_callee, total_call_sites)},
            "multiple_callees": {"count": multiple_callees, "pct": calc_cov(multiple_callees, total_call_sites)},
            "native_or_external_callees": {"count": native_or_ext_callees, "pct": calc_cov(native_or_ext_callees, total_call_sites)},
            "zero_caller_functions": {"count": len(zero_caller_functions), "pct": calc_cov(len(zero_caller_functions), len(functions))}
        },
        "packages": {
            "ground_truth_total": total_packages,
            "reachable": reachable_packages_count,
            "coverage_pct": calc_cov(reachable_packages_count, total_packages),
            "list_reachable": sorted(list(reachable_packages))
        },
        "files": {
            "ground_truth_total": total_files,
            "reachable": reachable_files_count,
            "coverage_pct": calc_cov(reachable_files_count, total_files)
        },
        "functions": {
            "combined_total": {
                "total": combined_total_functions,
                "reachable": combined_reachable_functions,
                "coverage_pct": calc_cov(combined_reachable_functions, combined_total_functions)
            },
            "js_functions": {
                "ground_truth_total": total_js_functions,
                "reachable": reachable_js_functions,
                "coverage_pct": calc_cov(reachable_js_functions, total_js_functions)
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


def generate_cross_language_stats(pkg, ver):
    version_param = ver if (ver and ver.strip()) else "latest"
    possible_json = [
        os.path.join(settings.BASE_DIR, 'static', f"cross_analysis_{pkg}_{version_param}", f"{pkg}.json"),
        os.path.join(settings.BASE_DIR, 'static', f"cross_analysis_{pkg}_{version_param}", f"{pkg}-withflags.json"),
    ]
    
    jelly_path = next((p for p in possible_json if os.path.exists(p)), None)
    if not jelly_path:
        return None

    with open(jelly_path, 'r', encoding='utf-8') as f:
        jelly_data = json.load(f)

    # Υπολογισμός απευθείας πάνω στα δεδομένα του πραγματικού cross-language call graph
    return analyze_package_reachability(jelly_data, root_pkg_name=pkg)


def get_cross_reachability_barchart(stats):
    pkgs_st = stats["packages"]
    files_st = stats["files"]
    fns = stats["functions"]

    categories = ["Packages", "Files", "JS Funcs", "Gasket", "Ghidra", "Combined"]
    totals = [
        pkgs_st["ground_truth_total"], 
        files_st["ground_truth_total"], 
        fns["js_functions"]["ground_truth_total"], 
        fns["native_gasket"]["total"], 
        fns["native_ghidra"]["total"], 
        fns["combined_total"]["total"]
    ]
    reachables = [
        pkgs_st["reachable"], 
        files_st["reachable"], 
        fns["js_functions"]["reachable"], 
        fns["native_gasket"]["reachable"], 
        fns["native_ghidra"]["reachable"], 
        fns["combined_total"]["reachable"]
    ]

    x = np.arange(len(categories))
    width = 0.35

    plt.clf()
    fig, ax = plt.subplots(figsize=(8.5, 4.5), facecolor='none')
    ax.bar(x - width/2, totals, width, label='Ground Truth / Total', color='#38bdf8')
    ax.bar(x + width/2, reachables, width, label='Reachable', color='#22c55e')

    ax.set_facecolor('none')
    ax.set_ylabel('Count', color='#94a3b8')
    ax.set_title(f'Reachability Coverage - {stats["package"]}', color='#38bdf8', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(categories, color='#94a3b8', rotation=15)
    ax.tick_params(colors='#94a3b8')
    ax.legend(facecolor='#1e293b', edgecolor='none', labelcolor='white')
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True, dpi=200)
    buf.seek(0)
    uri = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return uri