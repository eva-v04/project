#!/bin/bash

# Απόλυτη διαδρομή προς τον κεντρικό φάκελο του Jelly
JELLY_ROOT="/home/eva/Ptuxiakh/jelly"

package_name=$1 
package_version=$2 

if [ -z "$package_name" ]; then
    echo "No package name provided"
    exit 1
fi
[ -z "$package_version" ] && package_version="latest"

# Διαδρομές προς τα βοηθητικά αρχεία (βεβαιωθείτε ότι βρίσκονται στο /home/eva/Ptuxiakh/jelly/)
MERGE_SCRIPT="$JELLY_ROOT/merge_results.js"
GENERATE_HTML_SCRIPT="$JELLY_ROOT/generate_final_callgraph.js"
JELLY_MAIN="$JELLY_ROOT/lib/main.js"
TEMPLATE_HTML="$JELLY_ROOT/resources/visualizer.html"

folder_name="analysis_${package_name}_${package_version}"
mkdir -p "$folder_name"
cd "$folder_name"

# 1. Jelly Analysis
# Παράγει το αρχικό JSON και το api_results.json μέσα στον τρέχοντα φάκελο
node "$JELLY_MAIN" --api-usage --external-matches \
  -j "./${package_name}-withflags.json" \
  "./node_modules/${package_name}"

# 2. Merge Results
# ΠΡΟΣΟΧΗ: Χρησιμοποιούμε το api_results.json που μόλις φτιάχτηκε στον τρέχοντα φάκελο (.)
if [ -f "./api_results.json" ]; then
    node "$MERGE_SCRIPT" "./${package_name}-withflags.json" "./api_results.json"
else
    # Αν το Jelly το έβγαλε ένα επίπεδο πάνω
    node "$MERGE_SCRIPT" "./${package_name}-withflags.json" "$JELLY_ROOT/api_results.json"
fi

# 3. Generate Final HTML
node "$GENERATE_HTML_SCRIPT" "./merged_results.json" "./${package_name}-final.html" "$TEMPLATE_HTML"

echo "------------------------------------------------"
echo "Success! Final callgraph: ./${package_name}-final.html"