#!/usr/bin/env bash

PARENTSCRIPTPATH="$( cd "$(dirname "$0")" ; cd .. ; pwd -P )"
cd $PARENTSCRIPTPATH ; celery -A suap beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler