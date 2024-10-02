#!/usr/bin/env bash

PARENTSCRIPTPATH="$( cd "$(dirname "$0")" ; cd .. ; pwd -P )"

ARG1=${1:-foo}

PARAM=""
if [ $ARG1 == "--verbose" ]; then
    PARAM="-print"
fi

COUNT=`cd $PARENTSCRIPTPATH; find . -path ./deploy -prune -o -path ./upload -prune -o -name "*.pyc" | wc -l`

cd $PARENTSCRIPTPATH; find . -path ./deploy -prune -o -path ./upload -prune -o -name "*.pyc" $PARAM -exec rm {} +