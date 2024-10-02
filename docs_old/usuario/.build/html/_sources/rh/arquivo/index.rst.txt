.. _suap-rh-arquivo-index:

Arquivos
========

.. contents:: Conteúdo
    :local:
    :depth: 4

Introdução
----------

Finalidade
^^^^^^^^^^

O subsistema Arquivos permite manter, em formato digital, toda a documentação do servidor (pasta funcional digitalizada).

..
   Convenções
   ^^^^^^^^^^

   Para melhor apreensão deste manual, serão adotadas algumas convenções de conceitos e exibição de informações.

   Conceitos, Termos e Abreviações
   """""""""""""""""""""""""""""""

   .. include:: glossario.rst


Perfis envolvidos
-----------------

.. list-table::
   :widths: 40 60
   :header-rows: 1
   :stub-columns: 0

   * - Perfil
     - Descrição
   * - :ref:`Uploader <suap-rh-arquivo-perfil-uploader>`
     - Servidor cujo perfil de acesso possui permissão para **enviar** arquivos.
   * - :ref:`Identificador <suap-rh-arquivo-perfil-identificador>`
     - Servidor cujo perfil de acesso possui permissão para **identificar** arquivos. Esse perfil também
       pode **enviar** arquivos. 
   * - :ref:`Validador <suap-rh-arquivo-perfil-validador>`
     - Servidor cujo perfil de acesso possui permissão para **validar** arquivos. Esse perfil também
       pode **enviar** e **identificar** arquivos.

..
   Integração com outros Sistemas
   ------------------------------
   
   Sistema 1
   ^^^^^^^^^
   
   Especificar integração.
   
   Relacionamento com outros Subsistemas
   -------------------------------------
   
   Subsistema 1
   ^^^^^^^^^^^^
   
   Especificar relacionamento.

   
Módulo Upload (Envio) de Arquivos
---------------------------------

**Perfis envolvidos:** Uploader, Identificador e Validador.

.. list-table::
   :widths: 40 60
   :header-rows: 1
   :stub-columns: 0

   * - Operação
     - Finalidade
   * - :ref:`suap-rh-arquivo-enviar_arquivo`
     - Permite enviar arquivos.


Módulo Tratamento de Arquivos Pendentes
---------------------------------------

**Perfis envolvidos:** Identificador e Validador.

.. list-table::
   :widths: 40 60
   :header-rows: 1
   :stub-columns: 0

   * - Operação
     - Finalidade
   * - :ref:`suap-rh-arquivo-identificar_arquivo`
     - Permite identificar arquivos que foram enviados.
   * - :ref:`suap-rh-arquivo-validar_arquivo`
     - Permite validar arquivos que foram identificados.
