#!/usr/bin/bash -x 

set -e 

zipUrl=$1
targetFile=$2
targetFolder=$3

mkdir -p $(dirname $targetFile) $targetFolder

if [ ! -f $targetFile ]; then 
    curl -H "Authorization: token $GITHUB_ACTION" -o $targetFile $zipUrl
fi 

unzip $targetFile -d $targetFolder || true