FROM debian:bullseye as suap-base
ADD base.txt requirements.txt
ENV DEBIAN_FRONTEND noninteractive
ENV LANG pt_BR.UTF-8
ENV LANGUAGE pt_BR:pt
ENV LC_ALL pt_BR.UTF-8
RUN apt-get update
RUN export LANG=C.UTF-8
RUN apt-get install -y locales
RUN echo pt_BR.UTF-8 UTF-8 >> /etc/locale.gen
RUN locale-gen pt_BR.UTF-8
RUN apt-get install -y --fix-missing vim libpq-dev build-essential libffi-dev cargo \
    python3 python3-pip wget unzip git curl libsasl2-dev libldap2-dev libssl-dev procps \
    sudo libcairo2 libpango1.0 wkhtmltopdf ghostscript libmagic-dev poppler-utils zip
RUN ln -s /usr/bin/gs /usr/local/bin/gs
RUN pip3 install -r requirements.txt
RUN apt-get install -y libreoffice
RUN mkdir -p /opt/libreoffice5.0/program/
RUN ln -sfn /usr/bin/libreoffice /opt/libreoffice5.0/program/soffice
RUN ln -sfn /usr/bin/python3 /usr/bin/python
RUN sed -i s/clock/process_time/g /usr/local/lib/python3.9/dist-packages/xlrd/book.py

FROM suap-base as suap-app
RUN pip install python-ldap==3.3.1
CMD gunicorn -b 0.0.0.0:80 suap.wsgi:application -w 2 -t 360

FROM suap-base as suap-test

RUN apt-get install -y postgresql-13 postgresql-contrib-13
RUN rm /etc/postgresql/13/main/pg_hba.conf
RUN echo "fsync = off\nmax_locks_per_transaction = 1024" > /etc/postgresql/13/main/postgresql.auto.conf
RUN echo local   all             postgres                                trust > /etc/postgresql/13/main/pg_hba.conf
RUN echo host    all             all             127.0.0.1/32            trust >> /etc/postgresql/13/main/pg_hba.conf

RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN apt install -y ./google-chrome-stable_current_amd64.deb
RUN rm google-chrome-stable_current_amd64.deb
RUN curl -s https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$(google-chrome --version | cut -d ' ' -f 3 | cut -d . -f 1) > version.txt
RUN wget https://chromedriver.storage.googleapis.com/$(cat version.txt)/chromedriver_linux64.zip -O chromedriver.zip
RUN unzip chromedriver.zip
RUN rm version.txt chromedriver.zip
RUN mv chromedriver /usr/local/bin/

RUN pip install python-ldap==3.3.1
RUN printf \[supervisord\]\\nnodaemon=true\\n\[supervisorctl\]\\nserverurl=http://127.0.0.1:9001\\n\[inet_http_server\]\\nport=127.0.0.1:9001\\n\[rpcinterface:supervisor\]\\nsupervisor.rpcinterface_factory=supervisor.rpcinterface:make_main_rpcinterface\\n\[program:suap\]\\ncommand=gunicorn\ -b\ 0.0.0.0:80\ suap.wsgi:application\ -w\ 2\ -t\ 360\\ndirectory=/suap\\nuser=root\\nautostart=true\\nautorestart=true\\nstopasgroup=true\\nkillasgroup=true\\n > /etc/supervisord.conf
RUN pip install supervisor
CMD supervisord -s -c /etc/supervisord.conf -l /etc/supervisord.log

FROM suap-test as suap-dev
RUN pip install Werkzeug ipdb lorem django-debug-toolbar coverage ipython django_werkzeug graphviz

FROM suap-test as suap-ide
RUN wget https://github.com/cdr/code-server/releases/download/v3.12.0/code-server-3.12.0-linux-amd64.tar.gz
RUN tar -xzf code-server-3.12.0-linux-amd64.tar.gz
RUN ln -s /code-server-3.12.0-linux-amd64/bin/code-server /usr/local/bin/code-server
RUN mkdir /var/lib/code-server
RUN code-server --user-data-dir /var/lib/code-server --install-extension ms-python.python
RUN echo if ! [ -d /suap/deploy/code-server ]\; then cp -r /var/lib/code-server /suap/deploy/code-server\; fi > /bin/entrypoint.sh
RUN echo if ! [ -d /suap/deploy/postgres ]\; then pg_dropcluster 13 main \&\& pg_createcluster -d /suap/deploy/postgres 13 main -- --auth-local=trust\; fi >> /bin/entrypoint.sh
RUN echo /etc/init.d/postgresql start >> /bin/entrypoint.sh
RUN echo code-server --host 0.0.0.0 --user-data-dir /suap/deploy/code-server --auth password /suap >> /bin/entrypoint.sh
RUN chmod +x /bin/entrypoint.sh
CMD /bin/entrypoint.sh
# docker run --rm --name code-server -it -e PASSWORD=123 -p 8000:8000 -p 8080:8080 -v $(pwd):/suap -v  suap-test bash
