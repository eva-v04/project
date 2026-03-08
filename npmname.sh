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
folder_name="static/analysis_$package_name" #Ο φάκελος πρέπει να είναι στον φάκελο static Του προγράμματος 
mkdir -p "$folder_name" #-p;;;;;
cd "$folder_name" #Cd για να κατέβει σε αυτόν τον φάκελο το πακέτο

npm pack $package_name #κατεβάζω πακέτο

tar -xzf *.tgz --strip-components=1 # Αποσυμπιέζει αρχείο 
rm *.tgz #διαγράφει συμπιεσμένο αρχείο

jelly -j "$package_name.json" -m "$package_name.html" .
#τελεία γιατί είμαι ήδη στον φάκελο
