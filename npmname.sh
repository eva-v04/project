#!/bin/bash
#import nmp

echo "Give me the npm package name"
package_name=$1 #αντί για Read, παίρνουμε το όνομα από το πρώτο όρισμα
echo "Downloading $package_name"

# Έλεγχος αν δόθηκε όνομα
if [ -z "$package_name" ]; then
	echo "No package name provided"
	exit 1
fi

#προσωρινός φάκελος για την ανάλυση
folder_name="analysis_$package_name" 
mkdir -p "$folder_name" #-p;;;;;
cd "$folder_name" #Cd για να κατέβει σε αυτόν τον φάκελο το πακέτο

npm pack $package_name #κατεβάζω πακέτο
