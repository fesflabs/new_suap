#!/bin/bash
#set -e

DIR_BACKUP=/backup
DATABASE_BACKUP_FILENAME=$(ls $DIR_BACKUP/*.sql.gz)
DATABASE_RESTORE_FILENAME=$(ls $DIR_BACKUP/*.sql)

#echo "DATABASE_BACKUP_FILENAME: " $DATABASE_BACKUP_FILENAME
#echo "DATABASE_RESTORE_FILENAME: " $DATABASE_RESTORE_FILENAME

if [ ! -f "$DATABASE_RESTORE_FILENAME" -a -f "$DATABASE_BACKUP_FILENAME" ]; then
  echo ">>> Descompactando arquivo de backup ${_database_restore_filename} ..."
    gunzip -k $DATABASE_BACKUP_FILENAME
    DATABASE_RESTORE_FILENAME=$(ls $DIR_BACKUP/*.sql)
else
  echo "Arquivo de backup não encontrado no diretório $DIR_BACKUP ou arquivo dump já foi restaurado."
fi

echo ">>> Apagando base $POSTGRES_DB, caso exista"
echo ">>> Recriando base $POSTGRES_DB"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    DROP DATABASE IF EXISTS $POSTGRES_DB;
    CREATE DATABASE $POSTGRES_DB;
    GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DB TO $POSTGRES_USER;
EOSQL

DATABASE_RESTORE_FILENAME=$(ls /backup/*.sql)

echo ">>> Iniciando processo de restauração do dump ..."

if [ ! -z "$DATABASE_RESTORE_FILENAME" ]; then
  echo ">>> Restaurando dump $DATABASE_RESTORE_FILENAME ..."
  psql -U $POSTGRES_USER -d $POSTGRES_DB < $DATABASE_RESTORE_FILENAME
else
  echo "Arquiovo de dump não encontrado."
fi