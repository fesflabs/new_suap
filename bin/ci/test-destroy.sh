#!/usr/bin/env bash
set -axe
BRANCH="${1:-master}"
JOB_NAME=${2:test}
JOB_ID=${3:default}
CONTAINER="$JOB_NAME-$BRANCH-$JOB_ID"
docker stop "$CONTAINER" 2> /dev/null || true
