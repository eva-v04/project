import json
import os
import cxxfilt

def safe_demangle(mangled_name):
    if mangled_name and mangled_name.startswith("_Z"):  #;;;;
        try:
            return cxxfilt.demangle(mangled_name)
        except Exception:
            return mangled_name
    return mangled_name


def run_demangling():
    input_path = "/home/eva/Ptuxiakh/web/static/ghidra_sqlite3.json"
    output_path = "/home/eva/Ptuxiakh/demangled.json"

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    demangle_count = 0

    # Τρόπος Α: Αν οι συναρτήσεις είναι κλειδωμένες μέσα σε κάποιο key (π.χ. 'functions' ή 'nodes')
    # Ψάχνουμε σε όλα τα επίπεδα του αρχείου για dictionaries που έχουν το πεδίο 'name'
    
    def demangle(obj):
        nonlocal demangle_count
        if isinstance(obj, dict):
            if "name" in obj and isinstance(obj["name"], str):
                original = obj["name"]
                cleaned = safe_demangle(original)
                if cleaned != original:
                    obj["name"] = cleaned
                    demangle_count += 1
            for key, value in obj.items():
                demangle(value)
        elif isinstance(obj, list):
            for item in obj:
                demangle(item)

    #  ψάξιμο σε όλο το JSON
    demangle(data)

    #Αποθήκευση νέουjson
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f" demangling ολοκληρώθηκε!")
    print(f" Έγινε demangle σε {demangle_count} ονόματα συναρτήσεων.")
    print(f"Τοjson αρχείο αποθηκεύτηκε στο: {output_path}")

if __name__ == "__main__":
    run_demangling()