#!/bin/bash
#import nmp

echo "npm package name"
package_name=$1 
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

folder_name="analysis_${package_name}_${package_version}" #Ο φάκελος πρέπει να είναι στον φάκελο static Του προγράμματος 
mkdir -p "$folder_name" 
cd "$folder_name" #Cd για να κατέβει σε αυτόν τον φάκελο το πακέτο

rm -f "$package_name.json" "$package_name.html" #σβήνω παλιές αναλύσεις του πακέτου αν υπάρχουν

npm install --prefix . $package_name@$package_version  #κατεβάζω πακέτο
#prefix .  για να κατέβει το πακέτο στον φάκελο που είμαι

#jelly -j "${package_name}.json" -m "${package_name}.html" ./node_modules/${package_name}	
#lib/main.js --api-usage --external-matches -j ~/Ptuxiakh/${package_name}-withflags.json /node_modules/${package_name}

# Ορίζουμε το path του Jelly
JELLY_PATH="/home/eva/Ptuxiakh/jelly/lib/main.js" 

# Εκτέλεση της ανάλυσης
node "$JELLY_PATH" --api-usage --external-matches \
  -j "./${package_name}-withflags.json" \
  "./node_modules/${package_name}"