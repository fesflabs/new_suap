Preparando o ambiente de produção
=================================

.. contents:: Conteúdo
    :local:
    :depth: 4
    
Configurando para o uso
-----------------------

Pode-se dizer que o SUAP possui o seguinte fluxograma para instalação, configuração e uso:


.. figure:: media/fluxograma_uso_suap.png
   :align: center
   :scale: 100 %
   :alt: fluxograma para instalação/configuração/uso.
   :figclass: align-center
   
   Fluxograma para instalação, configuração e uso.
   
                                                                      
Instalação
----------


A instalação deve ser feita de acordo com instruções em [Instalação](Instalação)

Configuração inicial das variáveis do sistema
---------------------------------------------

Inicialmente deve-se preparar o ambiente, informando, nas configurações gerais do sistema, os dados da instituição. Para isso, é necessário ter em mãos as seguintes informações:

* Identificador SIAPE da Instituição: Sequência numérica de 5 caracteres que é utilizada para filtrar os dados nas Macros do Extrator SIAPE e SIAFI.
* Código UG da Instituição: Sequência numérica de 6 caracteres que identifica a unidade gestora responsável ou principal.

Também é necessário ter decidido qual será a árvore de setores que será utilizada:

* *Setores SIAPE:* Durante a importação, será criada apenas uma árvore com a organização de setores existente no SIAPE. Esta árvore, caso seja alterada no SUAP, será sobrescrita pelas informações existentes no SIAPE toda vez que houver uma nova importação de dados servidores.

* *Setores SUAP:* Durante a importação, serão criadas duas árvores de setores equivalentes SIAPE e SUAP, de acordo com a organização de setores existente no SIAPE. Entretanto, a árvores SUAP pode ser alterada no sistema e permanecerá inalterada caso haja uma nova importação de dados servidores. Essas duas árvores são paralelas e conectadas através de relacionamentos que referenciam os setores que são equivalentes nas duas árvores. Recomenda-se trabalhar com essa árvores por dois motivos principais: Primeiro, no SIAPE nem sempre temos todos os setores cadastrados, normalmente só os setores de níveis hierárquicos mais altos; Segundo, possíveis reformas nos setores do SIAPE causarão pouco ou nenhum impacto no funcionamento do sistema. 

Para configurar as informações gerais do sistema realize os seguintes passos:

* Faça login no SUAP com o administrador criado durante o processo de instalação. 
* Acesse a opção Administração no menu lateral direito.
* Clique em Configurações.
* Preencha os dados solicitados e envie as alterações.

Carga Inicial
-------------

O SUAP opera com dados pessoais e funcionais dos servidores oriundos do Sistema Integrado de Administração de Recuros Humanos do Governo Federal, o SIAPE. Dessa forma, é necessário fazer uma extração de dados desse sistema e inseri-los no SUAP.

A importação consiste de duas fases:

* :ref:`suap-desenvolvedor-extracao_siape`
* Importação dos arquivos extraídos para o SUAP

   * Após ter feito a extração dos dados do SIAPE, incluindo baixar os arquivos, para fazer a importação para SUAP, execute o seguinte comando::
   
      python manage.py importar_siape
   

Somente depois de realizado esses dois procedimentos com sucesso é que o SUAP estará pronto para utilização pelos usuários finais.
