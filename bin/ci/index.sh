#!/usr/bin/env bash
. .env

FULLPATH="$( cd "$(dirname "$0")" ; cd ../.. ; pwd -P )"
cd $FULLPATH

printf "server {server_name webmail.%s; location / { proxy_pass http://ci-mail-1:8025; }}\n" "$DOMAIN_NAME" > bin/ci/nginx/suapdevs.conf
while IFS= read -r name ; do
 if [ -n "$name" ]; then
  printf "server {
 server_name %s.$DOMAIN_NAME;
 location / {
  proxy_set_header Host $DOMAIN_NAME;
  proxy_pass http://deploy-%s;
 }
}
" "$name" "$name" >> bin/ci/nginx/suapdevs.conf
 fi
done <<< "$(docker ps -a --format '{{.Label "BRANCH"}}' | grep -v -e '^$')"

printf "
server {
 server_name rap-api.suapdevs.ifrn.edu.br;
 location / {
  proxy_set_header Host suapdevs.ifrn.edu.br;
  proxy_pass http://rap-rapconector-1:8040;
 }
}
server {
 server_name rap-sign.suapdevs.ifrn.edu.br;
 location / {
  proxy_set_header Host suapdevs.ifrn.edu.br;
  proxy_pass http://rap-rapsign-1:3000;
 }
}
" >> bin/ci/nginx/suapdevs.conf

docker exec ci-web-1 nginx -s reload
