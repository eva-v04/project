import json
import re
import Levenshtein


def extract_structural_tokens(fqn_string):
    """Διασπά ένα Fully Qualified Name στα βασικά δομικά του στοιχεία (Class,

    Method).
    Λειτουργεί γενικά για κάθε JavaScript/Native bridge pattern.
    """
    # Αφαίρεση των brackets/namespaces στην αρχή: <...> ή <...>()
    s = re.sub(r"^<[^>]+>(\(\))?", "", fqn_string)

    #  Αφαίρεση paths που περιέχουν slashes (π.χ. sqlite3/lib/...)
    if "/" in s:
        s = s.split("/")[-1]

    # Αφαίρεση συντακτικού θορύβου της JS και getters/setters της C++
    s = (
        s.replace("()", "")
        .replace(".prototype", "")
        .replace(".GET", "")
        .replace(".SET", "")
    )

    #  Split με βάση την τελεία για να βρούμε τα tokens
    tokens = [t.strip().lower() for t in s.split(".") if t.strip()]

    #  Φιλτράρισμα άχρηστων ενδιάμεσων λέξεων ( apply, constructor, binding)
    garbage_tokens = {"apply", "constructor", "binding", "node_sqlite3"}
    tokens = [t for t in tokens if t not in garbage_tokens]

    return tokens


def match_jelly_with_gasket(jelly_file, gasket_file, threshold=0.7):
    """Υβριδικός αλγόριθμος αντιστοίχισης με Structural Tokens, Depth Check

    και Levenshtein Distance για fallbacks.
    """
    # Σωστή φόρτωση των αρχείων
    with open(jelly_file, "r", encoding="utf-8") as f:
        jelly_data = json.load(f)
    with open(gasket_file, "r", encoding="utf-8") as f:
        gasket_data = json.load(f)

    # Συλλογή μοναδικών Jelly patterns από όλες τις κατηγορίες (read, write, call κλπ)
    jelly_patterns = set()
    for category in jelly_data.values():
        if isinstance(category, dict):
            for pattern in category.keys():
                jelly_patterns.add(pattern)

    gasket_bridges = gasket_data.get("bridges", [])

    # Αρχικοποίηση της λίστας αποτελεσμάτων
    results_mapping = []

    for j_pattern in jelly_patterns:
        j_tokens = extract_structural_tokens(j_pattern)
        if not j_tokens:
            continue

        best_match = None
        highest_similarity = 0

        for bridge in gasket_bridges:
            g_pattern = bridge["jsname"]
            g_tokens = extract_structural_tokens(g_pattern)

            # 1. STRICT DEPTH CHECK
            if len(j_tokens) != len(g_tokens):
                continue

            # Ένωση των tokens για τον έλεγχο Levenshtein
            j_clean_str = "".join(j_tokens)
            g_clean_str = "".join(g_tokens)

            similarity = Levenshtein.ratio(j_clean_str, g_clean_str)

            # 2. EXACT MATCH (Tier 1)
            if similarity == 1.0:
                highest_similarity = 1.0
                best_match = bridge
                break

            # 3. FUZZY MATCH VIA LEVENSHTEIN (Tier 2)
            if similarity > threshold and similarity > highest_similarity:
                highest_similarity = similarity
                best_match = bridge

        # Αποθήκευση αν βρέθηκε έγκυρο match
        if best_match:
            results_mapping.append(
                {
                    "jelly_pattern": j_pattern,
                    "gasket_jsname": best_match["jsname"],
                    "cfunc": best_match["cfunc"],
                    "confidence": round(highest_similarity, 2),
                }
            )

    return results_mapping


if __name__ == "__main__":
    mappings = match_jelly_with_gasket(
        "api_results.json", "bridges_sqlite3.json" #ΟΧΙ ΜΕ ΤΟ API_RESULTS
    )

    print("\n" + "=" * 60)
    print(f" Επιτυχείς Αντιστοιχίσεις: {len(mappings)}")
    print("=" * 60)

    # Εμφάνιση δείγματος
    print(json.dumps(mappings[:5], indent=2, ensure_ascii=False))

    # Αποθήκευση στο τελικό αρχείο
    with open("mapping_results.json", "w", encoding="utf-8") as f:
        json.dump(mappings, f, indent=2, ensure_ascii=False)
    print(
        "\n[*] Τα αποτελέσματα αποθηκεύτηκαν στο 'mapping_results.json'"
    )