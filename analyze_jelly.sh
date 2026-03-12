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
mkdir -p "$folder_name" 
cd "$folder_name" #Cd για να κατέβει σε αυτόν τον φάκελο το πακέτο

rm -f "$package_name.json" "$package_name.html" #σβήνω παλιές αναλύσεις του πακέτου αν υπάρχουν

npm install --prefix . $package_name  #κατεβάζω πακέτο
#prefix .  για να κατέβει το πακέτο στον φάκελο που είμαι

jelly -j "$package_name.json" -m "$package_name.html" ./node_modules/$package_name
