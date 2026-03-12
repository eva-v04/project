#!/bin/bash
#import gasket

read package_name

if [ -z "$package_name" ]; then
	echo "No package name provided" #! εκτυπώνεται στο terminal
	exit 1
fi

folder_name="static/gasket_analysis_$package_name"
mkdir -p "$folder_name"
cd $folder_name

npm install --prefix . $package_name

npx gasket -r $folder_name/node_modules/$package_name -o bridges_$package_name.json
