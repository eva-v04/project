import json
import os
import re
import io
import base64
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from django.conf import settings




def find_reachable_from_root(jelly_json, root_package_name):
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
    except Exception:
        pass
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
            if file.endswith(('.js', '.cjs', '.mjs')):
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

    all_callees_in_graph = {str(c) for _, c in fun2fun} | {str(c) for _, c in call2fun}
    zero_caller_functions = [fid for fid in functions.keys() if str(fid) not in all_callees_in_graph]

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

    pkg_ghidra_name = "lz4-napi" if root_pkg_name == "lz4" else root_pkg_name
    ghidra_file = os.path.join(settings.BASE_DIR, "static", f"ghidra_{pkg_ghidra_name}.json")
    if not os.path.exists(ghidra_file):
        ghidra_file = os.path.join(settings.BASE_DIR, "..", "web", "static", f"ghidra_{pkg_ghidra_name}.json")

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
            "zero_or_one_callee": {"count": zero_or_one_callee, "pct": calc_cov(zero_or_one_callee, total_call_sites)},
            "multiple_callees": {"count": multiple_callees, "pct": calc_cov(multiple_callees, total_call_sites)},
            "native_or_external_callees": {"count": native_or_ext_callees, "pct": calc_cov(native_or_ext_callees, total_call_sites)},
            "zero_caller_functions": {"count": len(zero_caller_functions), "pct": calc_cov(len(zero_caller_functions), len(functions))}
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




def generate_cross_language_stats(pkg, ver):
    # 1. Έλεγχος αν υπάρχει ήδη στο analysis_summary.json
    summary_paths = [
        os.path.join(settings.BASE_DIR, "analysis_summary.json"),
        os.path.join(settings.BASE_DIR, "..", "analysis_summary.json"),
        "/home/eva/Ptuxiakh/statistics/analysis_summary.json"
    ]
    
    for sum_path in summary_paths:
        if os.path.exists(sum_path):
            try:
                with open(sum_path, 'r', encoding='utf-8') as f:
                    summary_data = json.load(f)
                    for item in summary_data:
                        if item.get("package") == pkg:
                            return item
            except Exception:
                pass

    # 2. Dynamic Υπολογισμός αν πρόκειται για νέο πακέτο
    version_param = ver if (ver and ver.strip()) else "latest"
    possible_json = [
        os.path.join(settings.BASE_DIR, 'static', f"cross_analysis_{pkg}_{version_param}", f"{pkg}.json"),
        os.path.join(settings.BASE_DIR, 'static', f"cross_analysis_{pkg}_{version_param}", f"{pkg}-withflags.json"),
        os.path.join(settings.BASE_DIR, f"{pkg}-withflags.json"),
        f"/home/eva/Ptuxiakh/{pkg}-withflags.json"
    ]
    
    jelly_path = next((p for p in possible_json if os.path.exists(p)), None)
    if not jelly_path:
        return None

    with open(jelly_path, 'r', encoding='utf-8') as f:
        jelly_data = json.load(f)

    nm_dir = f"/home/eva/node_modules/{pkg}" if os.path.exists(f"/home/eva/node_modules/{pkg}") else "node_modules"
    lock_f = f"/home/eva/node_modules/{pkg}/package-lock.json" if os.path.exists(f"/home/eva/node_modules/{pkg}/package-lock.json") else "package-lock.json"

    return analyze_package_reachability(jelly_data, root_pkg_name=pkg, node_modules_dir=nm_dir, package_lock_file=lock_f)


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