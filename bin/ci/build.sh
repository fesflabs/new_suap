#!/usr/bin/env bash
set -axe

FULLPATH="$( cd "$(dirname "$0")" ; cd ../.. ; pwd -P )"
cd $FULLPATH

IMAGE="suap-${1:-base}"
if [ -z "$2" ]; then
  docker build -f bin/ci/Dockerfile -t "$IMAGE" --target "$IMAGE" requirements
else
  mkdir -p /tmp/build
  if [ "$2" = "packages" ]; then
    PACKAGES=$(docker run -w /suap --rm -v $FULLPATH:/suap suap-test sh -c "pip freeze > frozen-requirements.txt && grep -v -F -x -i -f frozen-requirements.txt requirements/base.txt | grep -v '#' | grep -v -e '^$' | tr '\n' ' '")
    printf "FROM %s\nRUN %s" "$IMAGE" "pip install -U $PACKAGES" > /tmp/build/Dockerfile
  else
    printf "FROM %s\nRUN %s" "$IMAGE" "$2" > /tmp/build/Dockerfile
  fi
  docker build -f /tmp/build/Dockerfile -t "$IMAGE" /tmp/build/
fi
