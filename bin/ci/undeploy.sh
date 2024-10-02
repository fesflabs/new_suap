#!/usr/bin/env bash
set -axe
. .env
while [ $# -gt 0 ]; do
   if [[ $1 == *"--"* ]]; then param="${1/--/}"; declare "$param"="$2"; fi
  shift
done

BRANCH_NAME=${branch:-none}
OWNER=${owner:-none}

if [ "$BRANCH_NAME" = "none" ] || [ "$OWNER" = "none" ]; then
  echo "Comando inválido, formato correto do comando: ./undeploy.sh --branch nomebranch --owner dono"
  exit 1
fi

CONTAINER_NAME="deploy-$BRANCH_NAME"
VOLUME_PATH="/home/gitlab-runner/$BRANCH_NAME"
SUAPDEVS_PATH="/var/suapdevs/$BRANCH_NAME"

docker exec ci-postgres-1 psql -U postgres -h "$DATABASE_HOST" -d suapdevs -tAc "INSERT INTO suapdevs (nome, dono, acao) VALUES ('$CONTAINER_NAME', '$OWNER', 'undeploy')" || true

docker stop $CONTAINER_NAME || true
sudo rm -rf $VOLUME_PATH $SUAPDEVS_PATH
