#!/usr/bin/env bash
set -axe

FULLPATH="$( cd "$(dirname "$0")" ; cd ../.. ; pwd -P )"
cd $FULLPATH

. .env

while [ $# -gt 0 ]; do
   if [[ $1 == *"--"* ]]; then param="${1/--/}"; declare "$param"="$2"; fi
  shift
done

BRANCH_NAME=${branch:-master}
DATABASE_TEMPLATE_NAME=${database:-${DATABASE_TEMPLATE}}
PASSWORD=${password:-$(openssl rand -hex 3)}
OWNER=${owner:-none}
DATABASE_NAME="database-$BRANCH_NAME-suap"
VOLUME_PATH="/var/suapdevs/$BRANCH_NAME"
CONTAINER_NAME=deploy-$BRANCH_NAME
CONTAINER=$(docker ps --format "{{.Names}}" -a --no-trunc --filter name=^/"$CONTAINER_NAME$")
DOCKER_EXEC="docker exec -e HOME=/tmp -w /suap $CONTAINER_NAME"
DATABASE=$( docker exec ci-postgres-1 psql -h "$DATABASE_HOST" -U postgres  -tAc "SELECT 1 FROM pg_database WHERE datname='$DATABASE_NAME'" )
SITE_URL="http://$BRANCH_NAME.$DOMAIN_NAME"

docker exec ci-postgres-1 psql -h "$DATABASE_HOST" -U postgres -d suapdevs -tAc "INSERT INTO suapdevs (nome, dono, acao) VALUES ('$CONTAINER_NAME', '$OWNER', 'deploy')"

if ! [ -d "$VOLUME_PATH" ]; then
  sudo cp -r $FULLPATH $VOLUME_PATH
fi

cd $VOLUME_PATH
sudo git checkout .
sudo git pull origin --no-edit $BRANCH_NAME
cd $FULLPATH

if ! [ "$DATABASE" ]; then docker exec ci-postgres-1 createdb -h "$DATABASE_HOST" -U postgres -T "$DATABASE_TEMPLATE_NAME" "$DATABASE_NAME"; fi

if ! [ "$CONTAINER" ]; then
  docker run --name $CONTAINER_NAME -e ELASTICSEARCH_URL="$ELASTICSEARCH_URL" --network=ci_suap-network --rm -it -d -v "$VOLUME_PATH":/suap -w /suap -e DATABASE_HOST="$DATABASE_HOST" -e DATABASE_NAME="$DATABASE_NAME" -e SITE_URL="$SITE_URL" -e EMAIL_HOST="ci-mail-1" -e EMAIL_PORT=1025 -p 80 -l suapdev -l OWNER="$OWNER" -l BRANCH="$BRANCH_NAME" -l PASSWORD="$PASSWORD" -l DATE="$(date +%d/%m/%Y)" suap-test
  $DOCKER_EXEC cp suap/settings_sample.py suap/settings.py
fi

$DOCKER_EXEC sh requirements/install.sh
$DOCKER_EXEC python manage.py sync
$DOCKER_EXEC supervisorctl restart suap

$DOCKER_EXEC python manage.py set_passwords_to "$PASSWORD";
echo "URL: $SITE_URL SENHA: $PASSWORD"
