#!/bin/bash
#import nmp

echo "Give me the npm package name"
read package_name
echo "Downloading $package_name"

#προσωρινός φάκελος για την ανάλυση
folder_name="analysis_$package_name" 
mkdir -p "folder_name" #-p;;;;;

npm pack $package_name

cd "$folder_name"
