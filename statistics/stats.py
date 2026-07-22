import json
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def load_json_data(filepath="analysis_summary.json"):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

# 

#  PNG
def generate_charts(data, output_dir="package_charts"):
    os.makedirs(output_dir, exist_ok=True)
    for pkg in data:
        name = pkg["package"]
        pkgs_st = pkg["packages"]
        files_st = pkg["files"]
        fns = pkg["functions"]

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

        plt.figure(figsize=(9, 5))
        plt.bar(x - width/2, totals, width, label='Ground Truth / Total', color='#4C72B0')
        plt.bar(x + width/2, reachables, width, label='Reachable', color='#55A868')

        plt.ylabel('Count')
        plt.title(f'Reachability Coverage Analysis - {name}')
        plt.xticks(x, categories, rotation=15)
        plt.legend()
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        chart_path = os.path.join(output_dir, f"{name}_reachability.png")
        plt.savefig(chart_path, dpi=300)
        plt.close()



def generate_global_summary_markdown(data):
    js_pkg_cov = [p["packages"]["coverage_pct"] for p in data]
    js_file_cov = [p["files"]["coverage_pct"] for p in data]
    js_func_cov = [p["functions"]["js_functions"]["coverage_pct"] for p in data]

    native_gasket_cov = [p["functions"]["native_gasket"]["coverage_pct"] for p in data]
    native_ghidra_cov = [p["functions"]["native_ghidra"]["coverage_pct"] for p in data]
    native_sum_cov = [p["functions"]["native_summary"]["coverage_pct"] for p in data]

    total_func_cov = [p["functions"]["combined_total"]["coverage_pct"] for p in data]

    def calc_stats(arr):
        arr_np = np.array(arr)
        p5 = np.percentile(arr_np, 5)
        mean = np.mean(arr_np)
        median = np.median(arr_np)
        p95 = np.percentile(arr_np, 95)
        return [f"{p5:.2f}%", f"{mean:.2f}%", f"{median:.2f}%", f"{p95:.2f}%"]

    table_rows = [
        ["JavaScript", "Package (%)", *calc_stats(js_pkg_cov)],
        ["JavaScript", "File (%)", *calc_stats(js_file_cov)],
        ["JavaScript", "Function (%)", *calc_stats(js_func_cov)],
        ["Binary/Native", "Gasket Function (%)", *calc_stats(native_gasket_cov)],
        ["Binary/Native", "Ghidra Function (%)", *calc_stats(native_ghidra_cov)],
        ["Binary/Native", "Native Total (%)", *calc_stats(native_sum_cov)],
        ["Total", "Combined Function (%)", *calc_stats(total_func_cov)]
    ]

    
    columns = ["Domain", "Granularity", "5%", "Mean", "Median", "95%"]
    summary_df = pd.DataFrame(table_rows, columns=columns)

    md_content = "# Overall Reachability & Bloat Analysis Report\n\n"
    md_content += "## 1. Global Statistical Summary\n\n"
    md_content += summary_df.to_markdown(index=False) + "\n\n"
    md_content += "---\n\n"
    return md_content




def generate_individual_package_markdown(pkg):
    name = pkg["package"]
    pkgs_st = pkg["packages"]
    files_st = pkg["files"]
    fns = pkg["functions"]
    
    table_data = [
        {"Category": "Packages (Dependencies)", "Total": pkgs_st["ground_truth_total"], "Reachable": pkgs_st["reachable"], "Coverage (%)": f"{pkgs_st['coverage_pct']:.2f}%"},
        {"Category": "Files (node_modules)", "Total": files_st["ground_truth_total"], "Reachable": files_st["reachable"], "Coverage (%)": f"{files_st['coverage_pct']:.2f}%"},
        {"Category": "JS Functions (Regex)", "Total": fns["js_functions"]["ground_truth_total"], "Reachable": fns["js_functions"]["reachable"], "Coverage (%)": f"{fns['js_functions']['coverage_pct']:.2f}%"},
        {"Category": "Native Gasket Code", "Total": fns["native_gasket"]["total"], "Reachable": fns["native_gasket"]["reachable"], "Coverage (%)": f"{fns['native_gasket']['coverage_pct']:.2f}%"},
        {"Category": "Native Ghidra Code", "Total": fns["native_ghidra"]["total"], "Reachable": fns["native_ghidra"]["reachable"], "Coverage (%)": f"{fns['native_ghidra']['coverage_pct']:.2f}%"},
        {"Category": "Combined Total Funcs", "Total": fns["combined_total"]["total"], "Reachable": fns["combined_total"]["reachable"], "Coverage (%)": f"{fns['combined_total']['coverage_pct']:.2f}%"},
    ]
    df = pd.DataFrame(table_data)
    
    md = f"### Package: `{name}`\n\n"
    md += df.to_markdown(index=False) + "\n\n"
    md += f"![{name} Chart](package_charts/{name}_reachability.png)\n\n"
    md += "---\n\n"
    return md


if __name__ == "__main__":
    json_path = "analysis_summary.json"
    md_output_path = "analysis_report.md"

    if os.path.exists(json_path):
        data = load_json_data(json_path)
        
        # Δημιουργία διαγραμμάτων PNG
        generate_charts(data)
        
        # Χτίσιμο Markdown αρχείου
        full_md = generate_global_summary_markdown(data)
        full_md += "## 2. Individual Package Reports\n\n"
        
        for pkg in data:
            full_md += generate_individual_package_markdown(pkg)
            
        # 3. Αποθήκευση ΜΟΝΟ στο αρχείο .md
        with open(md_output_path, "w", encoding="utf-8") as f:
            f.write(full_md)
            
        print(f"Η αναφορά δημιουργήθηκε επιτυχώς στο αρχείο '{md_output_path}'")
        print("Τα διαγράμματα αποθηκεύτηκαν στον φάκελο 'package_charts/'")
    else:
        print(f" Το αρχείο '{json_path}' δεν βρέθηκε!")