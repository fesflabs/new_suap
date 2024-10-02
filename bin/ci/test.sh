#!/usr/bin/env bash
set -axe
BRANCH=${1:-master}
CI_PROJECT_DIR=${2}/${3:tmp}
JOB_ID=${3}
JOB_NAME=${4:test}
SUAP_CHECK=${5}
SUAP_APPS=${6}
CONTAINER="$JOB_NAME-$BRANCH-$JOB_ID"
mkdir -p "$CI_PROJECT_DIR"
docker rm -f "$CONTAINER" || true
docker run --rm --name "$CONTAINER" -it -d -v "$(pwd)":/suap -v /tmp:/tmp -e SUAP_CHECK="$SUAP_CHECK" -e JOB_ID="$JOB_ID" -e SUAP_APPS="$SUAP_APPS" -e BEHAVE_CHROME_HEADLESS=1 -e CI_PROJECT_DIR="$CI_PROJECT_DIR" -v "$CI_PROJECT_DIR":"$CI_PROJECT_DIR" -w /suap suap-test

docker exec "$CONTAINER" /etc/init.d/postgresql start
docker exec "$CONTAINER" cp -r /suap /test
docker exec "$CONTAINER" createdb -U postgres suap_dev
docker exec -w /test "$CONTAINER" git pull origin "$BRANCH"
docker exec -w /test "$CONTAINER" git pull origin master
docker exec -w /test "$CONTAINER" cp suap/settings_sample.py suap/settings.py
docker exec -w /test "$CONTAINER" sh requirements/install.sh
docker exec -w /test "$CONTAINER" python manage.py collectstatic --skip-checks -v 0 --noinput
docker exec -w /test "$CONTAINER" python manage.py suap_check
