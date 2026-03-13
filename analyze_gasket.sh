#!/bin/bash
#import gasket

#docker pull grgalex/gasket:0.1.0
#docker run -ti --cap-add=SYS_PTRACE grgalex/gasket:0.1.0

read package_name

if [ -z "$package_name" ]; then
	echo "No package name provided" #! εκτυπώνεται στο terminal
	exit 1
fi

folder_name="$(pwd)/gasket_analysis_$package_name" #pwd Για να έχω full path
mkdir -p "$folder_name"
chmod 777 "$folder_name"

#npm install --prefix . $package_name
#gasket -r ./node_modules/$package_name -o bridges_$package_name.json

docker run --rm --cap-add=SYS_PTRACE \
	    -v "$folder_name:/results" \
	        grgalex/gasket:0.1.0 \
		    /bin/bash -c "    #για να τρέξουν οι εντολές μέσα στο Container
		    npm install $package_name && \
		    gasket -r ./node_modules/$package_name -o /results/bridges_$package_name.json
	    "
