#!/bin/bash
#se ocorrer algum erro interrompa a execução do script
############################# FUÇÕES UTILITÁRIAS #############################
##############################################################################

function in_array {
  ARRAY=$2
  for e in ${ARRAY[*]}
  do
    if [[ "$e" == "$1" ]]
    then
      return 0
    fi
  done
  return 1
}

function dict_get() {
  local _argkey=$1
  local _dict=$2
  for item in ${_dict[*]} ; do
    local key="${item%%:*}"
    local value="${item##*:}"
    if [ $key == $_argkey ]; then
      echo "$value"
    fi
  done
}

function dict_keys() {
  local _dict=$1
  local _keys=()
  for item in ${_dict[*]} ; do
    local key="${item%%:*}"
#    local value="${item##*:}"
    _keys+=($key)
  done
  echo ${_keys[*]}
}

function dict_values() {
  local _dict=$1
  local _values=()
  for item in ${_dict[*]} ; do
#    local key="${item%%:*}"
    local value="${item##*:}"
    _values+=($value)
  done
  echo ${_values[*]}
}

function string_to_array() {
  local _value=$1
  _array=(${_value//;/ })
  echo ${_array[*]}
}

function get_os_name() {
  unameOut="$(uname -s)"
  case "${unameOut}" in
      Linux*)     machine=Linux;;
      Darwin*)    machine=Mac;;
      CYGWIN*)    machine=Cygwin;;
      MINGW*)     machine=MinGw;;
      *)          machine="UNKNOWN:${unameOut}"
  esac
  echo ${machine}
}

function install_command_pv() {
  # https://stackoverflow.com/questions/19598797/is-there-any-way-to-show-progress-on-a-gunzip-database-sql-gz-mysql-pr
  # Comando pv é utilizado para mostrar a progressão da execução de outro comando.
  # command <the_command>     POSIX compatible
  # hash <the_command>        For regular commands. Or...
  # type <the_command>        #To check built-ins and keywords
  #verifica se o comando PV existe
  if command -v pv &> /dev/null
  then
      return
  fi
  if command -v port &> /dev/null
  then
    echo ">>> Instalando comando pv via macports ..."
    sudo port install pv
  elif command -v brew &> /dev/null
  then
    echo ">>> Instalando comando pv via Brew ..."
    brew install pv
  elif command -v brew &> /dev/null
  then
    echo ">>> Instalando comando pv via apt-get..."
    sudo apt-get update
    sudo apt-get install pv
  fi
}

function get_server_name() {
  _service_name_parse=$(dict_get "$1" "${DICT_ARG_SERVICE_PARSE[*]}")
  echo  ${_service_name_parse:-${1}}
}

GREEN_COLOR='\033[1;32m'
ORANGE_COLOR='\033[0;33m'
RED_COLOR='\033[0;31m'
BLUE_COLOR='\033[1;34m'
NO_COLOR='\033[0m'

function echo_warning() {
  echo ${@:3} -e "$ORANGE_COLOR WARN: $1$NO_COLOR"
}

function echo_danger() {
  echo ${@:3} -e "$RED_COLOR DANG: $1$NO_COLOR"
}

function echo_info() {
#  echo ${@:3} -e "$BLUE_COLOR INFO: $(date +\"%F\ %T\") $1$NO_COLOR"
  echo ${@:3} -e "$BLUE_COLOR INFO: $1$NO_COLOR"
}

function echo_success() {
  echo ${@:3} -e "$GREEN_COLOR SUCC: $1$NO_COLOR"
}


##################### CONVERTENDO ARRAY DO .ENV NA TAD DICT ##################
##############################################################################
#Se não existir o arquivo docker/dev/.env, copie o de docker/dev/.env.dev.example
if [ ! -f "docker/dev/.env" ]; then
  echo ">>> cp docker/dev/.env.dev.example docker/dev/.env"
  cp docker/dev/.env.dev.example docker/dev/.env
fi

source docker/dev/.env 2> /dev/null

if [ ! -f "docker/requirements/base.txt" ]; then
  echo ">>> cp -R requirements/ docker/requirements"
  cp -R requirements/ docker/requirements
fi

if [ ! -f "docker/dev/docker_pgadmin_servers.json" ]; then
  echo ">>> cp docker/dev/docker_pgadmin_servers_sample.json docker/dev/docker_pgadmin_servers.json"
  cp docker/dev/docker_pgadmin_servers_sample.json docker/dev/docker_pgadmin_servers.json
fi


#### Início do tratamento converter array do .env em TAD DICT
DICT_COMPOSES_FILES=()
for e in ${COMPOSES_FILES[*]}
do
  DICT_COMPOSES_FILES+=($e)
done

DICT_SERVICES_COMMANDS=()
for e in ${SERVICES_COMMANDS[*]}
do
  DICT_SERVICES_COMMANDS+=($e)
done

DICT_SERVICES_DEPENDENCIES=()
for e in ${SERVICES_DEPENDENCIES[*]}
do
  DICT_SERVICES_DEPENDENCIES+=($e)
done

DICT_ARG_SERVICE_PARSE=()
for e in ${ARG_SERVICE_PARSE[*]}
do
  DICT_ARG_SERVICE_PARSE+=($e)
done
#### Fim

export $(xargs <docker/dev/.env) 2> /dev/null
#export COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT_NAME

################################## DEFINIÇÕES ################################
##############################################################################

COMMANDS_COMUNS=(up down restart exec run logs shell)

POSTGRES_DB=${DATABASE_NAME:-$POSTGRES_DB}
POSTGRES_USER=${DATABASE_USER:-$POSTGRES_USER}
POSTGRES_PASSWORD=${DATABASE_PASSWORD:-$POSTGRES_PASSWORD}
POSTGRES_HOST=${DATABASE_HOST:-$POSTGRES_HOST}
POSTGRES_PORT=${DATABASE_PORT:-$POSTGRES_PORT}

ARG_SERVICE=$1
ARG_COMMAND=$2
ARG_OPTIONS="${@: 3}"
SERVICE_NAME=$(get_server_name ${ARG_SERVICE})
SERVICE_WEB_NAME=$(get_server_name "web")

CURRENT_DIRECTORY=$(pwd -P)
CURRENT_DIRECTORY=$(pwd -P)
_CURRENT_FILE_NAME=$(basename $0)
CURRENT_FILE_NAME="${_CURRENT_FILE_NAME%.*}"
CURRENT_FILE_NAME_PATH="$CURRENT_DIRECTORY/$CURRENT_FILE_NAME.sh"

#ln -sf $CURRENT_FILE_NAME_PATH /usr/local/bin/container


#### Início do tratamento para recuperar os arquivos docker-compose
_services=( $(dict_keys "${DICT_SERVICES_COMMANDS[*]}") )
_composes_files=()
for s in ${_services[*]}
do
  _file=$(dict_get "$s" "${DICT_COMPOSES_FILES[*]}")
  if [ ! -z "$_file" ]; then
    _composes_files+=("-f docker/dev/$_file")
  fi
done
COMPOSE="docker-compose ${_composes_files[*]}"
#echo ">>> $COMPOSE"
#### fim

POSTGRESQL="postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:$POSTGRES_PORT/"

############### FUNÇÕES RESPONSÁVEIS POR INSTACIAR OS SERVIÇOS ###############
##############################################################################
service_run() {
  local _option="${@: 2}"
  local _service_name=$1
  echo ">>> ${FUNCNAME[0]} $_service_name $_option"

  if [ $_service_name == $SERVICE_WEB_NAME ]; then
    $COMPOSE run --rm $_service_name $_option
  else
    $COMPOSE run $_service_name $_option
  fi
}

service_web_exec() {
  local _option="${@: 2}"
  local _service_name=$1
  echo ">>> ${FUNCNAME[0]} $_service_name $_option"

  if [[ `docker container ls | grep ${COMPOSE_PROJECT_NAME}_${_service_name}_1` ]]; then
    $COMPOSE exec $SERVICE_NAME $@
  else
    echo_info "O serviço não está em execução"
  fi
}

_service_exec() {
  local _option="${@: 2}"
  local _service_name=$1
  echo ">>> ${FUNCNAME[0]} $_service_name $_option"

  if [[ `docker container ls | grep ${COMPOSE_PROJECT_NAME}_${_service_name}_1` ]]; then
    $COMPOSE exec $_service_name $_option
  else
    service_run $_service_name $_option
  fi
}


service_exec() {
  local _option="${@: 2}"
  local _service_name=$1
  echo ">>> ${FUNCNAME[0]} $_service_name $_option"

  if [ $ARG_SERVICE == $SERVICE_WEB_NAME ]; then
    service_web_exec $_service_name $_option
  else
    _service_exec $_service_name $_option
  fi
}

service_shell() {
  local _option="${@: 2}"
  local _service_name=$1
  echo ">>> ${FUNCNAME[0]} $_service_name $_option"

  service_exec $_service_name bash $_option

#OCI runtime exec failed: exec failed: container_linux.go:380: starting container process caused: exec: "bash": executable file not found in $PATH: unknown
}

service_logs() {
  local _option="${@: 2}"
  local _service_name=$1
  echo ">>> ${FUNCNAME[0]} $_service_name $_option"

  if [ $_service_name == "all" ]; then
    echo_info "Status dos serviços"
    $COMPOSE logs -f $_option
  else
    $COMPOSE logs -f $_option $_service_name
  fi
}

database_db_backup() {
  local _option="$@"
  local _service_name="db"
  echo ">>> ${FUNCNAME[0]} $_service_name $_option"

  echo ">>> Compactando banco $POSTGRES_DB..."
  service_exec $_service_name pg_dump -U $POSTGRES_USER -d $POSTGRES_DB -Z 9 -f /backup/$POSTGRES_DB.sql.gz
  echo_info "Backup realizado com sucesso!"
}

function get_dir_backup() {
  if [ ! -z "$DATABASE_BACKUP_DIR" ]; then
    echo $DATABASE_BACKUP_DIR
  else
    echo $CURRENT_DIRECTORY/docker/backup
  fi
}

database_db_restore() {
  local _option="$@"
  local _service_name="db"
  echo ">>> ${FUNCNAME[0]} $_service_name $_option"

  install_command_pv

  DIR_BACKUP=$(get_dir_backup)
  DATABASE_BACKUP_FILENAME=$(ls $DIR_BACKUP/*.sql.gz)
  DATABASE_RESTORE_FILENAME=$(ls $DIR_BACKUP/*.sql)


  if [ ! -f "$DATABASE_RESTORE_FILENAME" -a -f "$DATABASE_BACKUP_FILENAME" ]; then
    _database_restore_filename="${DATABASE_BACKUP_FILENAME%.*}"
    echo ">>> Descompactando arquivo de backup ${_database_restore_filename} ..."
#    pv $DATABASE_BACKUP_FILENAME | gunzip > $_database_restore_filename
    gunzip -k $DATABASE_BACKUP_FILENAME
    DATABASE_RESTORE_FILENAME=$(ls $DIR_BACKUP/*.sql)
  else
    echo_warning "Arquivo de backup não encontrado no diretório $DIR_BACKUP."
  fi

  local _success=0
  echo ">>> Iniciando processo de restauração do dump ..."
  #restaura o banco caso encontre o arquivo de backup descompactado.
  if [ -f "$DATABASE_RESTORE_FILENAME" ]; then
    echo ">>> Restaurando dump $DATABASE_RESTORE_FILENAME"
    service_exec $_service_name /backup/init_database.sh
#    service_exec $_service_name /backup/init_database.sh | pv > /dev/null
    _success=1
  else
    echo "Arquiovo de dump não encontrado."
  fi

  echo ">>> A restauração foi concluído"
  return $_success

}

service_db_wait() {
  local _option="$@"
  local _service_name="db"
  echo ">>> ${FUNCNAME[0]} $_service_name $_option"

  echo_info "Aguardando a base de dados..."
  until $COMPOSE exec $_service_name pg_isready >/dev/null 2>&1 ; do
    E=$($COMPOSE logs --tail 1 $_service_name | tail -1)
    echo_warning "Postgres is unavailable - sleeping. ERROR: $E"
    sleep 1
  done

  echo_success "Conectado com sucesso"
}

_service_db_up() {
  local _option="${@: 2}"
  local _service_name=$1
  echo ">>> ${FUNCNAME[0]} $_service_name $_option"


  DIR_BACKUP=${POSTGRES_BACKUP_DIR:-$CURRENT_DIRECTORY/docker/backup}
  cp docker/dev/init_database.sh $DIR_BACKUP

  if [[ `docker container ls | grep sead_db_1` ]]; then
    echo_info "O banco já está em execução"
  else
    $COMPOSE up $_option $_service_name
    service_db_wait
  fi
}

command_web_django_manage() {
  local _option="$@"
  local _service_name=$SERVICE_NAME
  echo ">>> ${FUNCNAME[0]} $_service_name $_option"

  if [[ `docker container ls | grep ${COMPOSE_PROJECT_NAME}_${_service_name}_1` ]]; then
    service_exec $_service_name ./manage.py $_option
  else
    service_run $_service_name ./manage.py $_option
  fi
}

command_web_django_debug() {
  local _option="$@"
  local _service_name=$SERVICE_NAME
  echo ">>> ${FUNCNAME[0]} $_service_name $_option"

  $COMPOSE run --rm --service-ports $_service_name python manage.py runserver_plus 0.0.0.0:8000 $_option
}

_service_web_up() {
  local _option="${@: 2}"
  local _service_name=$1
  echo ">>> ${FUNCNAME[0]} $_service_name $_option"

  $COMPOSE up $_option $_service_name
}

_service_up() {
  local _option="${@: 2}"
  local _service_name=$1
  echo ">>> ${FUNCNAME[0]} $_service_name $_option"

  if [ $_service_name == "all" ]; then
      $COMPOSE up $_option
  elif [ $_service_name == "db" ]; then
    _service_db_up $_service_name $_option
  elif [ $_service_name == $SERVICE_WEB_NAME ]; then
    _service_web_up $_service_name $_option
  else
    local _nservice=$(get_server_name ${_service_name})
    $COMPOSE up $_option $_nservice
  fi
}

service_up() {
  local _option="${@: 2}"
  local _service_name=$1
  echo ">>> ${FUNCNAME[0]} $_service_name $_option"
  local _name_services=( $(string_to_array $(dict_get "$ARG_SERVICE" "${DICT_SERVICES_DEPENDENCIES[*]}") ) )
  for _nservice in ${_name_services[*]}
  do
    _service_up $_nservice -d
  done
  _service_up $_service_name $_option
}

_service_down() {
  local _option="${@: 2}"
  local _service_name=$1
  echo ">>> ${FUNCNAME[0]} $_service_name $_option"
  if [ $_service_name == "all" ]; then
      $COMPOSE down --remove-orphans $_option
  else
    if [[ `docker container ls | grep ${COMPOSE_PROJECT_NAME}_${_service_name}_1` ]]; then
      docker stop ${COMPOSE_PROJECT_NAME}_${_service_name}_1
      docker rm ${COMPOSE_PROJECT_NAME}_${_service_name}_1
    else
      echo_info "O serviço não está em execução"
    fi
  fi
}

service_down() {
  local _option="${@: 2}"
  local _service_name=$1
  echo ">>> ${FUNCNAME[0]} $_service_name $_option"
  _name_services=( $(string_to_array $(dict_get "$ARG_SERVICE" "${DICT_SERVICES_DEPENDENCIES[*]}") ) )
  _name_services=( $(string_to_array $(dict_get "$_service_name" "${DICT_SERVICES_DEPENDENCIES[*]}") ) )
  for _name_service in ${_name_services[*]}
  do
    _service_down $_name_service -v $_option
  done
  _service_down $_service_name $_option
}

service_restart() {
  local _option="${@: 2}"
  local _service_name=$1
  echo ">>> ${FUNCNAME[0]} $_service_name $_option"

#  if [ $_service_name == "all" ]; then
  service_down $_service_name $_option
  service_up $_service_name -d $_option
#  else
#    service_down $_service_name $_option
#    service_up $_service_name -d $_option
#  fi

}

service_undeploy() {
  local _option="${@: 2}"
  local _service_name=$1
  echo ">>> ${FUNCNAME[0]} $_service_name $_option"
  # Opção -v remove todos os volumens atachado
  service_down $_service_name -v $_option

  rm -rf docker/volumes
}

service_web_build() {
  local _option="${@: 2}"
  local _service_name=$1
  echo ">>> ${FUNCNAME[0]} $_service_name $_option"

  $COMPOSE build $SERVICE_WEB_NAME $_option
  service_up $SERVICE_WEB_NAME $_option
}

service_deploy() {
  local _option="${@: 2}"
  local _service_name=$1
  echo ">>> ${FUNCNAME[0]} $_service_name $_option"
  service_down $_service_name -v $_option
  service_web_build $SERVICE_WEB_NAME $_option
}

service_redeploy() {
  local _option="${@: 2}"
  local _service_name=$1
  echo ">>> ${FUNCNAME[0]} $_service_name $_option"
  service_undeploy
  service_deploy
}

service_status() {
  local _option="${@: 2}"
  local _service_name=$1
  echo ">>> ${FUNCNAME[0]} $_service_name $_option"

  $COMPOSE ps -a
}

command_db_psql() {
  local _option="${@: 2}"
  local _service_name=$1
  echo ">>> ${FUNCNAME[0]} $_service_name $_option"

  service_exec $_service_name psql -U $POSTGRES_USER $_option
  #-d $POSTGRES_DB $@
}

############################# ORIENTAÇÕES DE USO #############################
##############################################################################
DIR_BACKUP=$(get_dir_backup)

__usage="
Usar: $CURRENT_FILE_NAME [NOME_SERVICO] [COMANDOS] [OPCOES]
Nome do serviço:
  all                         Representa todos os serviços
  web                         Serviço rodando a aplicação SUAP
  db                          Serviço rodando o banco PostgreSQL
  pgadmin                     [Só é iniciado sob demanda]. Deve ser iniciado após o *db* , usar o endereço http://localhost:8001 , usuário **admin@pgadmin.org** , senha **admin** .
  redis                       Serviço rodando o cache Redis
  celery                      [Só é iniciado sob demanda]. Serviço rodando a aplicacão SUAP ativando a fila de tarefa assíncrona gerenciada pelo Celery
  elastic                     [Só é iniciado sob demanda]. Serviço rodando o Elasticsearch, ferramenta de busca e análise de dados distribruído. Sobe automaticamente o Kibana.
  opensearch                  [Só é iniciado sob demanda]. Serviço rodando o Opensearch, uma distribuição do Elasticsearch mantindo pela Amazon.  Sobe automaticamente o Opensearch Dashboard personalizado.


Comandos:

  Comando comuns: Comandos comuns a todos os serciços, exceto **all**
    up                        Sobe o serviço [NOME_SERVICO] em **foreground**
    down                      Para o serviço [NOME_SERVICO]
    restart                   Para e reinicar o serviço [NOME_SERVICO] em **background**
    exec                      Executar um comando usando o serviço [NOME_SERVICO] já subido antes, caso não tenha um container em execução, o comando é executado em em um novo container
    run                       Executa um comando usando a imagem do serviço [NOME_SERVICO] em um **novo** serviço
    logs                      Exibe o log do serviço [NOME_SERVICO]
    shell                     Inicia o shell (bash) do serviço [NOME_SERVICO]

  Comandos específicos:

    all:
      deploy                  Implanta os serviços, deve ser executado no primeiro uso, logo após o
      undeploy                Para tudo e apaga o banco, útil para quando você quer fazer um reset no ambiente
      redeploy                Faz um **undeploy** e um **deploy**
      status                  Lista o status dos serviços
      restart                 Reinicia todos os serviços em ****background***
      logs                    Mostra o log de todos os serviços
      up                      Sobe todos os serviços em **foreground**
      down                    Para todos os serviços

    web:
      build                Constrói a imagem da aplicação web
      makemigrations       Executa o **manage.py makemigrations**
      manage               Executa o **manage.py**
      migrate              Executa o **manage.py migrate**
      shell_plus           Executa o **manage.py shell_plus**
      debug                Inicia um serviço com a capacidade de usar o **breakpoint()** para **debug**

    db:
      psql                 Executa o comando **psql** no serviço
      wait                 Prende o console até que o banco suba, útil para evitar executar **migrate** antes que o banco tenha subido completamente
      backup               Realiza o backup do banco no arquivo $DIR_BACKUP/$POSTGRES_DB.sql.gz
      restore              Restaura o banco do arquivo *.sql ou *.gz que esteja no diretório $DIR_BACKUP

Opções: faz uso das opções disponíveis para cada [COMANDOS]

ˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆ
"

################ TRATAMENTO PARA VALIDAR OS ARGUMENTOS PASSADOS ##############
##############################################################################
number_arguments=$#

_commands_specific=( $(string_to_array $(dict_get "$ARG_SERVICE" "${DICT_SERVICES_COMMANDS[*]}") ) )
_services=( $(dict_keys "${DICT_SERVICES_COMMANDS[*]}") )
_commands_all=("${_commands_specific[@]}")
_commands_all+=("${COMMANDS_COMUNS[@]}")

error_info_message=""
error_danger_message=""
#if [ $number_arguments -eq 0 ]; then
#  error_danger_message="Argumento [NOME_SERVICO] não informado."
#  error_info_message="Serviços disponíveis: ${_services[*]} "
#el
if [ $number_arguments -eq 1 ]; then
  error_danger_message="Argumento [COMANDOS] não informado."
  error_info_message="Comandos disponíeis: \n\t\tcomuns: ${COMMANDS_COMUNS[*]} \n\t\tespecíficos: ${_commands_specific[*]}"
fi
#elif [ $number_arguments -ge 2 ]; then

service_exists=true
if [ $number_arguments -eq 0 ]; then
  error_danger_message="Argumento [NOME_SERVICO] não informado."
  error_info_message="Serviços disponíveis: ${_services[*]} "
elif  ! in_array "$ARG_SERVICE" "${_services[*]}"; then
  error_danger_message="Serviço [$ARG_SERVICE] não existe."
  error_info_message="Serviços disponíveis: ${_services[*]} "
  service_exists=false
fi
#fi

if [ $service_exists = true ] && [ $number_arguments -eq 2 ]; then
  if ! in_array "$ARG_COMMAND" "${_commands_all[*]}"; then
    if [ $ARG_SERVICE == "all" ]; then
      COMMANDS_COMUNS=()
    fi
    error_danger_message="Comando [$ARG_COMMAND] não existe para o serviço [$ARG_SERVICE]."
    error_info_message="Comandos disponíeis: \n\t\tcomuns: ${COMMANDS_COMUNS[*]} \n\t\tespecíficos: ${_commands_specific[*]}"
  fi
fi

if [ ! -z "$error_info_message" ]; then
  echo_info "$__usage"
  echo_danger "$error_danger_message"
  echo_warning " $error_info_message

        Usar: $CURRENT_FILE_NAME [NOME_SERVICO] [COMANDOS] [OPCOES]
        Role para cima para demais detalhes dos argumentos [NOME_SERVICO] [COMANDOS] [OPCOES]
    "
  exit 1
fi
#echo_info "Serviço: $SERVICE_NAME, argumento: $ARG_COMMAND"
#echo_info "SERVICE: ${ARG_SERVICE}  "
#echo_info "COMMAND: ${ARG_COMMAND}  "
#echo_info "CONTAINER: ${SERVICE_NAME}  "
#echo_info "OPTIONS: ${ARG_OPTIONS}  "
############################### BLOCO PRINCIPAL ##############################
##############################################################################
_service_name=$(get_server_name ${ARG_SERVICE})

if [ $ARG_COMMAND == up ]; then
  service_up ${_service_name} $ARG_OPTIONS
elif [ $ARG_COMMAND == down ]; then
  service_down ${_service_name} $ARG_OPTIONS
elif [ $ARG_COMMAND == restart ]; then
  service_restart ${_service_name} $ARG_OPTIONS
elif [ $ARG_COMMAND == exec ]; then
  service_exec ${_service_name} $ARG_OPTIONS
elif [ $ARG_COMMAND == run ]; then
  service_run ${_service_name} $ARG_OPTIONS
elif [ $ARG_COMMAND == logs ]; then
  service_logs ${_service_name} $ARG_OPTIONS
elif [ $ARG_COMMAND == shell ]; then
  service_shell ${_service_name} $ARG_OPTIONS

#for all containers
elif [ $ARG_COMMAND == status ]; then
  service_status ${_service_name} $ARG_OPTIONS
elif [ $ARG_COMMAND == undeploy ]; then
  service_undeploy ${_service_name} $ARG_OPTIONS
elif [ $ARG_COMMAND == deploy ]; then
  service_deploy ${_service_name} $ARG_OPTIONS
elif [ $ARG_COMMAND == redeploy ]; then
  service_redeploy ${_service_name} $ARG_OPTIONS

#for db containers
elif [ $ARG_COMMAND == psql ]; then
  command_db_psql ${_service_name} $ARG_OPTIONS
elif [ $ARG_COMMAND == restore ]; then
  database_db_restore ${_service_name} $ARG_OPTIONS
elif [ $ARG_COMMAND == backup ]; then
  database_db_backup ${_service_name} $ARG_OPTIONS

#for web containers
elif [ $ARG_COMMAND == build ]; then
  service_web_build ${_service_name} $ARG_OPTIONS
elif [ $ARG_COMMAND == manage ]; then
  command_web_django_manage $ARG_OPTIONS
elif [ $ARG_COMMAND == makemigrations ]; then
  command_web_django_manage makemigrations
elif [ $ARG_COMMAND == migrate ]; then
  command_web_django_manage migrate
elif [ $ARG_COMMAND == shell_plus ]; then
  command_web_django_manage shell_plus
elif [ $ARG_COMMAND == debug ]; then
  command_web_django_debug $ARG_OPTIONS
else:
  echo_warning "Comando $ARG_COMMAND sem função associada"
fi
