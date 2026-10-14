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
source /home/eva/Ptuxiakh/web/djangoenv/bin/activate

WEB_STATIC="/home/eva/Ptuxiakh/web/static"
OUTPUT_DIR="$WEB_STATIC/cross_analysis_${package_name}_${package_version}"
mkdir -p "$OUTPUT_DIR"

# Αρχείο Bridges από το Gasket
GASKET_BRIDGES="$WEB_STATIC/gasket_analysis_${package_name}_${package_version}/bridges_${package_name}.json"

# Mangled JSON Αρχείο από το Ghidra
GHIDRA_MANGLED_JSON="$WEB_STATIC/ghidra_${package_name}.json"

# Τελικά Αρχεία Εξόδου του Cross-Language Call Graph
OUTPUT_JSON="$OUTPUT_DIR/${package_name}.json"
OUTPUT_HTML="$OUTPUT_DIR/${package_name}.html"

# Εντοπισμός του σωστού φακέλου node_modules
SPECIFIC_NM="$WEB_STATIC/analysis_${package_name}_${package_version}/node_modules/${package_name}"
GLOBAL_NM="/home/eva/node_modules/${package_name}"

if [ -d "$SPECIFIC_NM" ]; then
    TARGET_DIR="$SPECIFIC_NM"
elif [ -d "$GLOBAL_NM" ]; then
    TARGET_DIR="$GLOBAL_NM"
else
    TARGET_DIR="$WEB_STATIC/gasket_analysis_${package_name}_${package_version}/node_modules/${package_name}"
fi

echo "Target directory for Jelly analysis: $TARGET_DIR"

# Μετάβαση στον φάκελο του Jelly και Εκτέλεση
cd /home/eva/Ptuxiakh/jelly

EXTRA_ARGS=""

# Έλεγχος ύπαρξης Bridges
if [ ! -f "$GASKET_BRIDGES" ] || [ ! -s "$GASKET_BRIDGES" ]; then
    echo "CRITICAL: Δεν βρέθηκε το αρχείο bridges ($GASKET_BRIDGES). Αδυναμία εκτέλεσης Cross-Language ανάλυσης."
    exit 1
fi

EXTRA_ARGS="--bridges $GASKET_BRIDGES"

if [ -f "$GHIDRA_MANGLED_JSON" ] && [ -s "$GHIDRA_MANGLED_JSON" ]; then
    EXTRA_ARGS="$EXTRA_ARGS --ghidra $GHIDRA_MANGLED_JSON"
fi

echo "Running Jelly with args: $EXTRA_ARGS"

node lib/main.js --api-usage --external-matches \
  $EXTRA_ARGS \
  -j "$OUTPUT_JSON" \
  -m "$OUTPUT_HTML" \
  "$TARGET_DIR"

echo "Η Cross-Language ανάλυση ολοκληρώθηκε! Τα αποτελέσματα σώθηκαν στο: $OUTPUT_DIR"