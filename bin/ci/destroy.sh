#!/usr/bin/env bash
set -axe

FULLPATH="$( cd "$(dirname "$0")" ; cd ../.. ; pwd -P )"
cd $FULLPATH

. .env

while [ $# -gt 0 ]; do
   if [[ $1 == *"--"* ]]; then param="${1/--/}"; declare "$param"="$2"; fi
  shift
done

BRANCH_NAME=${branch:-none}
OWNER=${owner:-none}
CONTAINER_NAME="deploy-$BRANCH_NAME"

if [ "$BRANCH_NAME" = "none" ] || [ "$OWNER" = "none" ]; then
  echo "Comando inválido, formato correto do comando: ./destroy.sh --branch nomebranch --owner dono"
  exit 1
fi

VOLUME_PATH="/home/gitlab-runner/$BRANCH_NAME"
SUAPDEVS_PATH="/var/suapdevs/$BRANCH_NAME"
DATABASE_NAME="database-$BRANCH_NAME-suap"
docker stop $CONTAINER_NAME || true
docker exec ci-postgres-1 psql -U postgres -h "$DATABASE_HOST" -d suapdevs -tAc "INSERT INTO suapdevs (nome, dono, acao) VALUES ('$CONTAINER_NAME', '$OWNER', 'destroy')" || true
docker exec ci-postgres-1 psql -U postgres -h "$DATABASE_HOST" -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DATABASE_NAME'" || true
docker exec ci-postgres-1 dropdb -U postgres -h "$DATABASE_HOST" "$DATABASE_NAME" || true
sudo rm -rf $VOLUME_PATH $SUAPDEVS_PATH
