.. _suap-desenvolvedor-extracao_siape:

Extração dos arquivos do SIAPE
==============================


A extração dos arquivos do SIAPE é feita acessando o `Serviço de Emulação do Serpro`_

.. _`Serviço de Emulação do Serpro`: http://acesso.serpro.gov.br/

Antes de prosseguir, é interessante ler o Manual do Usuário do Extrator de Dados – SIAPE, disponível para download (apenas usuários do sistema) no Portal Siapenet para familizarizar-se com a utilização da extração. Como resultado da extração, são gerados dois tipos de arquivos. Um tipo de arquivo com extensão TXT e outro com extensão REF. Os arquivos TXT contém todos os dados extraídos propriamente ditos. Os arquivos REF, possuem os metadados, isto é, a descrição do layout de como as informações estão distribuídas nos arquivos TXT.

Devido às limitações de acesso ao SIAPE e a quantidade de servidores presente nas instituições, dividimos a extração semanal em vários arquivos.

Extração SIAPE
--------------

Durante a extração, serão adquiridos os dados para que  todas as tabelas da base do SUAP sejam preenchidas, permitindo precisão em todos os relatórios estatísticos e quantitativos da aplicação RH. 

É possível realizar a extração completa dos dados do SIAPE Executando a macro de extração completa, _macro_siape.mac_. Esta macro é obtida acessando o SUAP com um superusuário, clicando em:
 _Administração --> Baixar Macro SIAPE_ no menu lateral direito.


Além dos dados importados a partir dessa extração, também existem os dados de Contra-cheque, que são obtidos através da Fita-Espelho.

Executando a macro
^^^^^^^^^^^^^^^^^^

Uma macro Host On-Demand é um script XML que permite a um cliente HOD interagir automaticamente com um aplicativo rodando na sessão de emulador de terminal SIAPE. Uma macro HOD geralmente é escrita para realizar uma tarefa específica ou conjunto de tarefas no terminal.

A _macro_siape.mac_ foi escrita para extrair os dados das tabelas contidas no processo de extração completa do SIAPE. Automatizando, desta forma, o processo de extração de dados dos servidores da instituição.

Para rodar a macro no emulador de terminal SIAPE, execute os seguintes passos:
 
* Acesse o HOD da rede SERPRO em http://acesso.serpro.gov.br
* Clique em Acesso ao HOD, no menu superior direito
* Informe CPF e senha de acesso
* Será aberto um terminal java em que deverá ser informado, novamente, usuário, senha e o sistema que deseja acessar.
* Escolha a aplicação EXCOEXARQ que realiza consulta e extração de arquivos no terminal.
* Na próxima tela, comece a executar a macro, clicando no ícone verde na barra superior do sistema correspondente ao circulado na figura abaixo:

`Botao para Execução da macro`_

.. _`Botao para Execução da macro`: https://bitbucket.org/ifrn/suap/downloads/Terminal3.png

* Escolha o arquivo .mac baixado do SUAP para ser executado e aguarde o fim da execução.

Após feita a extração, será necessário baixar os arquivos gerados, conforme abaixo.

Baixando os arquivos
^^^^^^^^^^^^^^^^^^^^

**OPÇAO 1 - Quem ainda não tem TOKEN SIAPE**

* abra o terminal na pasta do suap e execute o comando:
*python manage.py rh_baixar_arquivos_siape*

Lembre-se que para o comando funcionar é necessário que o suap esteja corretamente configurado.

**OPÇÃO 2 - ARQUIVOS ZIPADOS VIA SUAP**

* Entre no [Portal Siapenet](siapenet.gov.br) com seu token
* Clique no menu do lado esquerdo obtenção e envio de arquivos
* Escolha a opção arquivos extrator
* Baixe os arquivos em uma pasta e compacte-os no formato ".zip"
* Entre no SUAP na opção de configurações (permitida pra quem é ADMIN no SUAP)
* Clique no link "Upload Arquivos Extrator"

