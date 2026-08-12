#!/bin/bash


package_name=$1
package_version=$2

if [ -z "$package_name" ]; then
    echo "Σφάλμα: Δεν δόθηκε όνομα πακέτου."
    exit 1
fi

if [ -z "$package_version" ]; then
    package_version="latest"
fi

# ΕΝΕΡΓΟΠΟΙΗΣΗ VIRTUAL ENVIRONMENT
# !Εξασφαλίζει ότι το demangle.py θα βρίσκει το cxxfilt ακόμα και όταν καλείται από το Web App
source /home/eva/Ptuxiakh/web/djangoenv/bin/activate


WEB_STATIC="/home/eva/Ptuxiakh/web/static"
OUTPUT_DIR="$WEB_STATIC/cross_analysis_${package_name}_${package_version}"
mkdir -p "$OUTPUT_DIR"

# Αρχείο Bridges από το Gasket
GASKET_BRIDGES="$WEB_STATIC/gasket_analysis_${package_name}_${package_version}/bridges_${package_name}.json"

# Mangled JSON Αρχείο από το Ghidra (Το Jelly θα εκτελέσει το demangle.py πάνω σε αυτό)
GHIDRA_MANGLED_JSON="$WEB_STATIC/ghidra_${package_name}.json"

# Τελικά Αρχεία Εξόδου του Cross-Language Call Graph
OUTPUT_JSON="$OUTPUT_DIR/${package_name}.json"
OUTPUT_HTML="$OUTPUT_DIR/${package_name}.html"

# Μετάβαση στον φάκελο του Jelly και Εκτέλεση
cd /home/eva/Ptuxiakh/jelly

node lib/main.js --api-usage --external-matches \
  --bridges "$GASKET_BRIDGES" \
  --ghidra "$GHIDRA_MANGLED_JSON" \
  -j "$OUTPUT_JSON" \
  -m "$OUTPUT_HTML" \
  "/home/eva/node_modules/${package_name}"

echo "Η Cross-Language ανάλυση ολοκληρώθηκε! Τα αποτελέσματα σώθηκαν στο: $OUTPUT_DIR"