#!/bin/bash
#import nmp

echo "Give me the npm package name"
read package_name
echo "Downloading $package_name"

#προσωρινός φάκελος για την ανάλυση
folder_name="analysis_$package_name" 
mkdir -p "$folder_name" #-p;;;;;
cd "$folder_name" #Cd για να κατέβει σε αυτόν τον φάκελο το πακέτο

npm pack $package_name #κατεβάζω πακέτο
