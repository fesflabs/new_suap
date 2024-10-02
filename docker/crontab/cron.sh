#!/bin/bash

echo "Iniciando o serviço do cron"
cp /opt/suap/docker/crontab/tasks /etc/crontab
chmod 0644 /etc/crontab
cat /etc/crontab
cron -f