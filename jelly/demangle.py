import json
import os
import cxxfilt #Pip install cxxfilt
import sys 

def safe_demangle(mangled_name):
    try:
        return cxxfilt.demangle(mangled_name)
    except Exception:
        return mangled_name

def run_demangling():
    # Έλεγχος αν δόθηκαν τα σωστά ορίσματα από το Jelly
    if len(sys.argv) < 3:
        print("Σφάλμα: Λείπουν ορίσματα.")
        print("Χρήση: python3 demangle.py <input_ghidra_json> <output_demangled_json>")
        sys.exit(1)

    input_path = sys.argv[1]   # Το αρχικό αρχείο της Ghidra
    output_path = sys.argv[2]  # Πού θα αποθηκευτεί το demangled

    if not os.path.exists(input_path):
        print(f"Σφάλμα: Το αρχείο {input_path} δεν υπάρχει.")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    demangle_count = 0
    
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

    demangle(data)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f" [PYTHON] Demangling ολοκληρώθηκε! Έγιναν {demangle_count} αντικαταστάσεις.")

if __name__ == "__main__":
    run_demangling()