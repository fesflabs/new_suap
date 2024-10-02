:orphan:

Instalar pacotes Debian
=======================
    sudo apt-get python-simplejson python-dev postgresql-8.4 build-essential lncurses5-dev git-core subversion

Baixar fontes do suap
=====================

    git clone git@bitbucket.org:ifrn/suap.git

Instalar demais dependencias do SUAP
====================================

    cd suap    
    svn co https://suapsvn.ifrn.edu.br/djtools/trunk djtools
    sudo pip install -U -r requirements.txt

Arquivo de configuração do SUAP
===============================

    cp sample_settings.py settings.py

Configurando o banco de dados
=============================

    No arquivo settings.py, a variável DATABASE_HOST deve guardar o ip da máquina onde está o banco de dados. Por padrão, ela é 'localhost'
    sudo vim /etc/postgresql/8.4/main/pg_hba.conf
    Substitua:
    local   all         postgres                          ident sameuser
    Por:
    local   all         postgres                          trust
    Substitua:
    host    all         all         127.0.0.1/32          md5
    Por:
    host    all         all         127.0.0.1/32          trust
    Reinicie o serviço:
    sudo /etc/init.d/postgresql-8.4 restart
    psql -U postgres -c "create database suap with encoding 'utf-8'"

Sincronizando o banco de dados e permissões de acesso
=====================================================

    python manage.py syncdb
	python manage.py sync

Preparando o suap para operar
=============================

    python manage.py carga_inicial

Caso utilize o almoxarifado, é necessário executar o sql
========================================================

	python manage.py dbshell < almoxarifado/sql/funcoes.sql

Executando o SUAP usando o Web Server do Django
===============================================

    python manage.py runserver 0.0.0.0:8000
    http://localhost:8000

Configurando o Apache
=====================

    chown -R www-data.www-data /tmp
	apt-get install apache2 libapache2-mod-wsgi
	python manage.py create_apache_files server_name=suap.ifrn.local server_admin=suap@naoresponder.ifrn.edu.br
	cp suap /etc/apache2/sites-available
	a2ensite suap
	/etc/init.d/apache2 reload

Driver com Microsoft SQL Server (organizar e deixar arquivos no nosso redmine para evitar perdê-los)
====================================================================================================

	wget http://ibiblio.org/pub/Linux/ALPHA/freetds/current/freetds-current.tgz
	tar -xvf freetds-current.tgz
	cd freetds-0.92.dev.20120312/
	sudo ./configure
	sudo make
	sudo make install

	wget http://cython.org/release/Cython-0.16.tar.gz
	tar -xvf Cython-0.16.tar.gz
	cd Cython-0.16/
	sudo python setup.py install

	wget http://pymssql.googlecode.com/files/pymssql-2.0.0b1-dev-20111019.tar.gz
	tar -xvf pymssql-2.0.0b1-dev-20111019.tar.gz
	cd pymssql-2.0.0b1-dev-20111019/
	sudo python setup.py install
	
