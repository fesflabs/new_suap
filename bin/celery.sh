#!/usr/bin/env bash

PARENTSCRIPTPATH="$( cd "$(dirname "$0")" ; cd .. ; pwd -P )"
CELERY_QUEUE=${1:-geral}
cd $PARENTSCRIPTPATH ; celery -A suap worker -l INFO -Q $CELERY_QUEUE