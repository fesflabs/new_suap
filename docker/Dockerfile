FROM debian:bullseye as suap-base
ENV DEBIAN_FRONTEND noninteractive
ENV LANG pt_BR.UTF-8
ENV LANGUAGE pt_BR:pt
ENV LC_ALL pt_BR.UTF-8
ENV TZ="America/Fortaleza"
RUN export LANG=C.UTF-8
RUN sed -i -e's/ main/ main contrib non-free/g' /etc/apt/sources.list && \
    apt-get update && apt-get install -y --fix-missing locales vim openssh-server git build-essential \
        python-dev python-setuptools nginx cron \
        libldap2-dev libsasl2-dev libpq-dev ghostscript \
        libjpeg-dev libfreetype6-dev zlib1g-dev \
        freetds-dev libxmlsec1-dev libxml2-dev libxslt1-dev \
        libblas-dev liblapack-dev libatlas-base-dev gfortran \
        libglu1-mesa libcairo2 libcups2 libdbus-glib-1-2 libxinerama1 libsm6 \
        tmpreaper libgdk-pixbuf2.0-0 libffi-dev shared-mime-info \
        python3-dev python3-pip python3-setuptools python3-wheel \
        python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
        poppler-utils ntpdate swig libreoffice openssl libssl-dev libxrender-dev  \
        git-core libx11-dev libxext-dev ttf-mscorefonts-installer libfontconfig1-dev fontconfig curl
RUN echo "pt_BR.UTF-8 UTF-8" >> /etc/locale.gen
RUN echo "America/Fortaleza" >> /etc/timezone
RUN locale-gen pt_BR.UTF-8
RUN ln -s /usr/bin/gs /usr/local/bin/gs
ADD ./requirements /requirements
RUN pip3 install --no-cache-dir -r /requirements/production.txt
RUN mkdir -p /opt/libreoffice5.0/program/ && ln -sfn /usr/bin/libreoffice /opt/libreoffice5.0/program/soffice
RUN ln -sfn /usr/bin/python3 /usr/bin/python
RUN rm -rf /var/lib/apt/lists/*
RUN curl -L https://github.com/wkhtmltopdf/wkhtmltopdf/releases/download/0.12.4/wkhtmltox-0.12.4_linux-generic-amd64.tar.xz -o /root/wkhtmltox.tar.xz
RUN tar -xvf /root/wkhtmltox.tar.xz -C /root && mv /root/wkhtmltox/bin/wkhtmlto* /usr/bin && fc-cache -f -v
RUN chown -R www-data.www-data /var/www
RUN python -c "import nltk; nltk.download('punkt', download_dir='/var/www/nltk_data'); nltk.download('stopwords', download_dir='/var/www/nltk_data'); "
WORKDIR /opt/suap

FROM suap-base as suap-app
ADD --chown=www-data:www-data . .
RUN cp suap/settings_sample.py suap/settings.py && mkdir -p deploy/logs/history && chown -R www-data:www-data /opt/suap
RUN cp docker/crontab/tasks /etc/crontab && chmod 0644 /etc/crontab
USER www-data
RUN python manage.py collectstatic -c --no-input -v 0 && ./bin/clean_pyc.sh
CMD ["gunicorn", "-b 0.0.0.0:8000", "suap.wsgi:application", "-w 2", "-t 360", "--max-requests", "1000", "--max-requests-jitter", "30"]

FROM suap-base as suap-dev
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN apt install -y ./google-chrome-stable_current_amd64.deb
RUN apt-get update && apt-get install -y zip postgresql-client-13
RUN rm google-chrome-stable_current_amd64.deb
RUN curl -s https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$(google-chrome --version | cut -d ' ' -f 3 | cut -d . -f 1) > version.txt
RUN wget https://chromedriver.storage.googleapis.com/$(cat version.txt)/chromedriver_linux64.zip -O chromedriver.zip
RUN unzip chromedriver.zip
RUN rm version.txt chromedriver.zip
RUN mv chromedriver /usr/local/bin/
RUN pip3 install --no-cache-dir -r /requirements/development.txt
CMD python manage.py runserver 0.0.0.0:8000
