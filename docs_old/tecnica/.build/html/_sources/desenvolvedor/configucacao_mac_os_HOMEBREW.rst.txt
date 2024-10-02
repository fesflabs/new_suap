Configurando o Ambiente de Desenvolvimento Mac OS (HomeBrew)
============================================================

.. contents:: Conteúdo
    :local:
    :depth: 4
    

Instalando o Certificado Digital (requerido pelo Git)
-----------------------------------------------------

O instalador do HomeBrew baixa alguns arquivos do GitHub utilizando HTTPS. Para corrigir os erros de certificado digital execute os comandos a seguir:


.. code:: python

   sudo curl http://curl.haxx.se/ca/cacert.pem > /tmp/cacert.pem
   cd /usr/share/curl
   sudo mv curl-ca-bundle.crt  old.curl-ca.-bundle.crt
   sudo mv /tmp/cacert.pem curl-ca-bundle.crt



Instalando o XCode
------------------

O X-Code está presente no CD original do Mac, mas pode-se também baixar do site: http://developer.apple.com/tools/xcode/. Ficar atento para baixar a versão compatível com a versão do Mac OS X

**OBS:** se estiver utilizando o mac os leopard (10.5.x), utilize a vers 3.1.4 do xCode.

No MacOS Mountain Lion é necessário instalar o "Command Line Tools" (PIP mostra erro no LLVM/GCC).

1. Abra o XCODE;
1.     Clique em PREFERÊNCIAS -> DOWNLOAD
1.     Instale o "Command Line Tools";


Instalando o HomeBrew
---------------------

Antes de instalar o HomeBrew desinstale o MacPorts (se estiver utilizando):


.. code:: python

   http://bitboxer.de/2010/06/03/moving-from-macports-to-homebrew/


O comando a seguir não pode ser executado como super-usuário (sudo)

.. code:: python

   /usr/bin/ruby <(curl -fsSkL raw.github.com/mxcl/homebrew/go)



Instalando o Git
^^^^^^^^^^^^^^^^

É necessário instalar o GIT antes de executar o update no Brew (pré-requisito).

.. code:: python
   brew install git



Atualizando o Brew
^^^^^^^^^^^^^^^^^^

.. code:: python

   brew update



Configurando Pip
----------------

O PIP é instalado juntamente com Python 2.7 (via Brew). Para facilitar a chamada ao comando pode ser criado um link simbólico:

.. code:: python

   sudo ln -s /usr/local/share/python/pip-2.7 /usr/local/bin/pip-2.7

No caso de MacOS Mountain Lion onde o Python 2.7 já vem pré-instalado, é necessário instalar o Pip via easy_install.


.. code:: python

   easy_install pip


Instalando pacotes via Pip
--------------------------


.. code:: python

   sudo pip-2.7 install django==1.3.3
   sudo pip-2.7 install PIL
   sudo pip-2.7 install python-ldap==2.3.13
   sudo pip-2.7 install reportlab
   sudo pip-2.7 install pypdf



Instalando Postgres
-------------------

Antes de instalar o PsycoPG2 é necessário instalar Postgres (o PsycoPG2 depende de algumas bibliotecas da pasta lib do Postgres)

Para instalar o Postgres baixe o instalador (.DMG) na URL a seguir:

.. code:: python

   http://get.enterprisedb.com/postgresql/postgresql-9.0.8-1-osx.dmg


Instalando wget
---------------

Utilizado para baixar os fontes do PsycoPG2


.. code:: python

   brew install wget



Instalando o pacote PsycoPG2
----------------------------

Baixando os fontes do PsycoPG2

Instalando via PIP: 


.. code:: python

   sudo pip install psycopg2==2.4.1


Se não funcionar, instale manualmente:


.. code:: python

   cd
   wget http://initd.org/psycopg/tarballs/PSYCOPG-2-4/psycopg2-2.4.1.tar.gz
   tar -zxvf psycopg2-2.4.1.tar.gz
   cd psycopg2-2.4.1


Utilize um editor de textos (ex.: vi) para modificar o arquivo "setup.cfg".


.. code:: python

   have_ssl=0
   static_libpq=0
   pg_config=/Library/PostgreSQL/9.0/bin/pg_config
   library_dirs=/Library/PostgreSQL/9.0/lib
   libraries=/usr/lib


Após efetuar as alterações no "setup.cfg", efetue o build e install no package.


.. code:: python

   sudo python2.7 setup.py build
   sudo python2.7 setup.py install


Corrigindo conflitos de bibliotecas ("Incompatible library version: _psycopg.so requires version 1.0.0 or later, but libssl")


.. code:: python

   cd /usr/lib
   sudo unlink libcrypto.dylib
   sudo unlink libssl.dylib 
   sudo ln -s /Library/PostgreSQL/9.0/lib/libcrypto.1.0.0.dylib /usr/lib/libcrypto.dylib
   sudo ln -s /Library/PostgreSQL/9.0/lib/libssl.1.0.0.dylib /usr/lib/libssl.dylib
   sudo ln -s /Library/PostgreSQL/9.0/lib/libcrypto.1.0.0.dylib /usr/lib/libcrypto.1.0.0.dylib
   sudo ln -s /Library/PostgreSQL/9.0/lib/libssl.1.0.0.dylib /usr/lib/libssl.1.0.0.dylib



Baixando os fontes do SUAP
--------------------------

Efetuando checkout do código do SUAP via SVN

.. code:: python

   cd
   mkdir Workspace
   cd Workspace
   svn co https://suapsvn.ifrn.edu.br/suap/trunk suap --username SEU_LOGIN


Removendo arquivos *.pyc do versionamento
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


.. code:: python

   cd ~/.subversion
   vi config


No arquivo "config" procure por "global-ignores" e inclua *.pyc (e remova o comentário no início da linha / ponto e vírgula)


.. code:: python

   global-ignores = *.pyc *.o *.lo *.la #*# .*.rej *.rej .*~ *~ .#* .DS_Store


Instalando a IDE
^^^^^^^^^^^^^^^^

Baixe o Aptana

.. code:: python

   http://www.aptana.com/products/studio3/download
