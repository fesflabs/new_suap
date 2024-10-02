# SUAP CI

## Instalação
1 - Instale o "git" caso ele ainda não esteja instalado.
> apt-get install git

2 - Gere um token de acesso no Gitlab para definir uma URL no seguinte formato: https://oauth2:XXXXXXX@gitlab.ifrn.edu.br/cosinf/suap.git e clone o repostório.
> git clone {url} /opt/suap

3 - Acesse o diretório do projeto.
> cd /opt/suap

4 - Instale os softwares necessários.
> bin/ci/configure.sh

5 - Edite o arquivo .env criado na raíz do projeto.
> vim .env

6 - Gere as imagens do SUAP.
> bin/ci/build.sh base
>
> bin/ci/build.sh test

7 - Inicialize o gitlab-runner e os containers.
> bin/ci/start.sh

8 - Registre os containers no nginx.
> bin/ci/index.sh

9 - Crie o banco template.
> bin/ci/createdb.sh

10 - Crie o banco de log
> bin/ci/createlog.sh

11 - Crie um ambiente de homologação para testar a instalação.
> bin/ci/deploy.sh --branch "master" --owner "admin" --database "suap_dev"  --password "123"

12 - Remova o ambiente provisoriamente.
> bin/ci/undeploy.sh --branch "master" --owner "admin"

13 - Recrie o ambiente de teste.
> bin/ci/deploy.sh --branch "master" --owner "admin" --database "suap_dev"  --password "123"

14 - Remova o ambiente definitivamente.
> bin/ci/destroy.sh --branch "master" --owner "admin"
