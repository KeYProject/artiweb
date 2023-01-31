#!/usr/bin/bash -x 

set -e 

zipUrl=$1
targetFile=$2
targetFolder=$3

mkdir -p $(dirname $targetFile) $targetFolder

if [ ! -f $targetFolder ]; then 
    if [ ! -f $targetFile ]; then 
        wget --header="Authorization: token $PRIVATE_TOKEN" -O $targetFile $zipUrl
    fi 

    unzip $targetFile -d $targetFolder || true
fi