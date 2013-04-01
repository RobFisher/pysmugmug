#!/bin/bash

mypath=`dirname $0`
echo $mypath

dirnames=`ls * -d`
for d in $dirnames
do
    pushd . > /dev/null
    cd $d
    if [ -f .smugmug ]
    then
        echo "Processing $d ..."
        $mypath/smugmug.py --auto --missing-files
    fi
    popd > /dev/null
done

