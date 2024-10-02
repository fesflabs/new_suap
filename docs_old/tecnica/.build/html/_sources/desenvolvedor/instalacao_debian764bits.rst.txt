Instalação no Debian 7 64 bits
==============================

.. contents:: Conteúdo
    :local:
    :depth: 4
    

O tutorial faz o deploy do suap com as seguintes configurações:

:SO: Debian 7 "wheezy" 64 bits
:SUAP: 13.10
:Python: 2.7.3 (debian 7 default)
:Django: 1.5.4
:Postgresql: 9.1 (debian 7 default)

Configurando o Debian
---------------------

Cerfifique-se que o arquivo ``/etc/apt/sources.list`` tenha o seguinte conteúdo (conteúdo original do debian 7 português)::

    deb http://ftp.br.debian.org/debian/ wheezy main
    deb-src http://ftp.br.debian.org/debian/ wheezy main
    deb http://security.debian.org/ wheezy/updates main contrib
    deb-src http://security.debian.org/ wheezy/updates main contrib
    deb http://ftp.br.debian.org/debian/ wheezy-updates main contrib
    deb-src http://ftp.br.debian.org/debian/ wheezy-updates main contrib

Configure o locale e o timezone do sistema::

    dpkg-reconfigure locales # configurar como pt_BR.UTF-8
    dpkg-reconfigure tzdata

Instale os pacotes debian no sistema::

    apt-get update
    apt-get install vim openssh-server git build-essential \
                    python-dev python-pip nginx supervisor \
                    libldap2-dev libsasl2-dev libpq-dev \
                    libjpeg-dev libfreetype6-dev zlib1g-dev \
                    freetds-dev

Configure as libs para instalação do pacote python **PIL**::

    ln -s /usr/lib/x86_64-linux-gnu/libz.so /usr/lib/libz.so
    ln -s /usr/lib/x86_64-linux-gnu/libjpeg.so /usr/lib/libjpeg.so
    ln -s /usr/lib/x86_64-linux-gnu/libfreetype.so /usr/lib/libfreetype.so

Aumente o limite de arquivos manipulados pelo sistema (essa configuração é feita para um melhor funcionamento do **Nginx**) adicionando as seguintes linhas ao arquivo ``/etc/security/limits.conf``::

    *               soft     nofile           65536
    *               hard     nofile           65536
    root            soft     nofile           65536
    root            hard     nofile           65536

Configurando o banco de dados Postgres
--------------------------------------

Para instalar o Postgres::

    apt-get install postgresql

Logado como **root**, altere a senha do usuário **postgres**::

    su - postgres
    psql -c "ALTER USER postgres WITH ENCRYPTED PASSWORD 'minha-senha'"

Edite o arquivo de configuração ``/etc/postgresql/9.1/main/pg_hba.conf``, deixando com o seguinte conteúdo::

    local   all         postgres                          trust
    local   all         all                               ident
    host    all         all         127.0.0.1/32          md5
    host    all         all         IP_DO_SUAP/32         md5 # substitua IP_DO_SUAP pelo valor adequado

Reinicie o Postgresql::

    /etc/init.d/postgresql restart

Crie o banco de dados **suap**::

    psql -U postgres -c "create database suap with encoding 'utf-8'"
    psql -U postgres -c "ALTER DATABASE suap SET bytea_output TO 'escape'"

Configurando o SUAP
-------------------

Gere a chave SSH::

    ssh-keygen

No **Bitbucket**, acesse *Administration -> Deployment Keys -> Add key*, defina um "Label" e cole o conteúdo da chave pública (arquivo ``/root/.ssh/id_rsa.pub``) no campo "Key" e clique em "Add key".

Baixe os fontes::

    cd /var/opt/
    git clone git@bitbucket.org:ifrn/suap.git # substitua "ifrn" por sua instituição se for o caso
    cd /var/opt/suap
    pip install -U -r deploy/requirements.txt

Crie o seu arquivo de configuração::

    cp settings_sample.py settings.py

Para gerar uma chave secreta, rode o seguinte comando::

    python manage.py generate_secret_key

Edite o arquivo ``settings.py``, definindo o resultado do comando anterior na variável SECRET_KEY_. Edite também as variáveis DATABASES_ e ALLOWED_HOSTS_.

.. _SECRET_KEY: https://docs.djangoproject.com/en/1.5/ref/settings/#std:setting-SECRET_KEY
.. _DATABASES: https://docs.djangoproject.com/en/1.5/ref/settings/#databases
.. _ALLOWED_HOSTS: https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts

Configurando o gunicorn, nginx e supervisor::

    cp deploy/templates/gunicorn_start.sh deploy/gunicorn_start.sh
    chmod +x deploy/gunicorn_start.sh
    cp deploy/templates/suap.conf.supervisor /etc/supervisor/conf.d/suap.conf
    cp deploy/templates/suap.nginx /etc/nginx/sites-enabled/suap
    chown -R www-data.www-data deploy

Nota: faça as modificações conforme o caso, especialmente o **server_name** do arquivo ``/etc/nginx/sites-enabled/suap``.

Prepare o SUAP::

    python manage.py syncdb
    python manage.py collectstatic # jah cria a pasta deploy/static
    python manage.py sync
    python manage.py carga_inicial

Comandos para gerência do serviço SUAP::

    supervisorctl reload
    supervisorctl status
    supervisorctl start suap
    /etc/init.d/nginx start