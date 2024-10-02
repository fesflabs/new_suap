CURRENT_DIRECTORY := $(shell pwd)

COMMAND?=python manage.py shell

SERVICES?=web nginx cron celery celery-beat celery-flower redis db web-dev celery-dev minio minio-nginx

export USER_UID=33
export USER_GID=33

include .env
export $(shell sed 's/=.*//' .env)
export COMPOSE_PROJECT_NAME=suap

COMPOSE=docker-compose -f docker/docker-compose.prod.yml -f docker/docker-compose.dev.yml
PSQL=$(COMPOSE) run --rm db psql "postgresql://$(DATABASE_USER):$(DATABASE_PASSWORD)@$(DATABASE_HOST):$(DATABASE_PORT)/"

help:
	@echo "Docker Compose Help"
	@echo "-----------------------"
	@echo ""
	@echo "Para iniciar o serviço web em produção:"
	@echo "    make start-web"
	@echo ""
	@echo "Para iniciar o serviço celery em produção:"
	@echo "    make start-celery"
	@echo ""
	@echo "Para iniciar o serviço cron em produção:"
	@echo "    make start-cron"
	@echo ""
	@echo "Para iniciar o serviço redis:"
	@echo "    make start-redis"
	@echo ""
	@echo "Para iniciar o serviço postgres:"
	@echo "    make start-db"
	@echo ""
	@echo "Para iniciar o ambiente de desenvolvimento (sem redis nem postgres):"
	@echo "    make start-web-dev"
	@echo ""
	@echo "Para parar os serviços:"
	@echo "    make stop"
	@echo ""
	@echo "Para remover os serviços:"
	@echo "    make down"
	@echo ""
	@echo "Para compilar as imagens do suap:"
	@echo "    make build"
	@echo ""
	@echo "Para listar os logs dos containers:"
	@echo "    make logs"
	@echo ""
	@echo "Para limpar os arquivos pyc:"
	@echo "    make clean-pyc"
	@echo ""
	@echo "Para executar um comando específico do container:"
	@echo "    make execute COMMAND='ls'"
	@echo ""
	@echo "Para rodar o sync do banco do suap:"
	@echo "    make sync"
	@echo ""
	@echo "Para acessar o bash do container web:"
	@echo "    make bash"
	@echo ""
	@echo "Para rodar o migrate do banco do suap:"
	@echo "    make migrate"
	@echo ""
	@echo "Para rodar o makemigrations do banco do suap:"
	@echo "    make makemigrations"
	@echo ""
	@echo "Para rodar o collectstatic do container web:"
	@echo "    make collectstatic"
	@echo ""
	@echo "Para rodar o clean-pyc:"
	@echo "    make clean-pyc"
	@echo ""
	@echo "Para inicializar um banco vazio do suap:"
	@echo "    make begin"
	@echo ""
	@echo "Para rodar o psql do banco do suap:"
	@echo "    make psql"
	@echo ""
	@echo "Para rodar o redis-cli do redis do suap:"
	@echo "    make redis-cli"
	@echo ""

runserver:
	python manage.py runserver 0.0.0.0:8000

start-web:
	$(COMPOSE) --profile prod up -d --scale web=1 --scale nginx=0 --scale cron=0 --scale celery=0 --scale celery-beat=0 --scale celery-flower=0
	$(COMPOSE) --profile prod up -d --scale web=$(CONTAINERS) --scale nginx=1 --scale cron=0 --scale celery=0 --scale celery-beat=0 --scale celery-flower=0

start-celery:
	$(COMPOSE) --profile prod up -d celery

start-celery-beat:
	$(COMPOSE) --profile prod up -d celery-beat

start-flower:
	$(COMPOSE) --profile prod up -d celery-flower

start-cron:
	$(COMPOSE) --profile prod up -d cron

start-minio:
	$(COMPOSE) --profile minio up -d --scale minio=$(CONTAINERS) --scale nginx-minio=1

start-redis:
	$(COMPOSE) --profile redis up -d

start-db:
	$(COMPOSE) --profile db up -d

start-web-dev:
	$(COMPOSE) --profile dev up web-dev

start-celery-dev:
	$(COMPOSE) --profile dev up -d celery-dev

stop:
	$(COMPOSE) stop $(SERVICES)

down: stop
	$(COMPOSE) rm -f $(SERVICES)
	docker-compose -f docker/docker-compose.cleanup.yml down -v

prune: down
	docker system prune -f

status:
	$(COMPOSE) ps

build:
	$(COMPOSE) build web

push-image:
	docker push $(SUAP_IMAGE)

pull-image:
	docker pull $(SUAP_IMAGE)

build-dev:
	$(COMPOSE) build web-dev

logs:
	$(COMPOSE) logs -f $(SERVICES)

clean-pyc:
	./bin/clean_pyc.sh

execute:
	$(COMPOSE) run --user $(USER_UID):$(USER_GID) --rm web $(COMMAND)

sync: COMMAND=python manage.py sync
sync: execute

bash:
	$(COMPOSE) run --user $(USER_UID):$(USER_GID) --rm -p 8001:8001 web /bin/bash

bash-dev:
	$(COMPOSE) run --user $(USER_UID):$(USER_GID) --rm -p 8000:8000 web-dev /bin/bash

bash-root:
	$(COMPOSE) run --user 0:0 --rm web /bin/bash

shell: COMMAND=python manage.py shell
shell: execute

migrate: COMMAND=python manage.py migrate
migrate: execute

makemigrations: COMMAND=python manage.py makemigrations
makemigrations: execute

collectstatic: COMMAND=python manage.py collectstatic -c --no-input -v 0
collectstatic: execute

begin:
	$(COMPOSE) run --rm web python manage.py test --nocoverage --noinput --failfast comum.tests.CreateDatabaseTestCase --keepdb
	$(PSQL) -c "ALTER DATABASE test_suap_dev RENAME TO $(DATABASE_NAME)"
	$(PSQL) -c "ALTER DATABASE $(DATABASE_NAME) SET bytea_output TO 'escape'"
	$(COMPOSE) run --rm web python manage.py migrate --fake
	$(COMPOSE) run --rm web python manage.py createsuperuser

psql:
	$(PSQL)

redis-cli:
	$(COMPOSE) run --rm redis redis-cli -u $(REDIS_LOCATION)

.PHONY: down help
