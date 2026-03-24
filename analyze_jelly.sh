#!/bin/bash
#import nmp

echo "npm package name"
package_name=$1 #αντί για Read, παίρνουμε το όνομα από το πρώτο όρισμα
package_version=$2 
echo "Downloading $package_name"

# Έλεγχος αν δόθηκε όνομα
if [ -z "$package_name" ]; then
	echo "No package name provided"
	exit 1
fi

if [ -z "$package_version" ]; then
	echo "No package version provided, using latest"
	package_version="latest"
fi

#προσωρινός φάκελος για την ανάλυση
folder_name="static/analysis_$package_name_$package_version" #Ο φάκελος πρέπει να είναι στον φάκελο static Του προγράμματος 
mkdir -p "$folder_name" 
cd "$folder_name" #Cd για να κατέβει σε αυτόν τον φάκελο το πακέτο

rm -f "$package_name.json" "$package_name.html" #σβήνω παλιές αναλύσεις του πακέτου αν υπάρχουν

npm install --prefix . $package_name@$package_version  #κατεβάζω πακέτο
#prefix .  για να κατέβει το πακέτο στον φάκελο που είμαι

jelly -j "$package_name.json" -m "$package_name.html" ./node_modules/$package_name
