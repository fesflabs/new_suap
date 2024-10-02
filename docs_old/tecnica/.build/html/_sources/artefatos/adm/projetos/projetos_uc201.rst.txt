.. include:: header.rst

.. _suap-artefatos-adm-projetos-uc201:

UC201 - Listar meus projetos <v0.1>
===================================

.. contents:: Conteúdo
    :local:
    :depth: 4

Histórico da Revisão
--------------------

.. list-table:: **Histórico da Revisão**
   :widths: 10 5 30 15
   :header-rows: 1
   :stub-columns: 0

   * - Data
     - Versão
     - Descrição
     - Autor
   * - 22/04/2014
     - 0.1
     - Início do Documento
     - Kelson da Costa Medeiros

Objetivo
--------

xxxx

Atores
------

Principais
^^^^^^^^^^
Gerente sistêmico

Interessado
^^^^^^^^^^^
Não se aplica.


Pré-condições
-------------
Edital deve estar cadastrado.


Pós-condições
-------------
Não se aplica.


Fluxo de Eventos
----------------


Fluxo Normal
^^^^^^^^^^^^
.. _FN:

    #. O caso de uso é iniciado selecionando a opção ``EXTENSÃO`` > ``Projetos`` > ``Editais``, visualiza um edital e seleciona a opção ``Adicionar anexo``
    #. O sistema apresenta a lista de anexos já cadastrados para o edital selecionado (RIN01_)
    #. O ator seleciona a opção ``Adicionar anexo``
    #. Na tela ``Adicionar anexo`` o ator preenche os campos (RIN02_)
    #. O ator finaliza o caso de uso selecionando a opção ``Salvar``
    #. O fluxo retorna para o ponto em que foi iniciado

Fluxo Alternativo
^^^^^^^^^^^^^^^^^

FA1 – Fluxo alternativo 1 (FN_-2) - Editar
""""""""""""""""""""""""""""""""""""""""""

#. O ator seleciona a opção ``Editar`` de uma das linhas da listagem de anexos já cadastrados
#. Na tela ``Editar anexo`` o ator altera os campos (RIN02_), os dados do anexo já virão preenchidos
#. O ator finaliza o caso de uso ao selecionar a opção ``Salvar``
#. O sistema apresenta a listagem do passo FN-2


FA2 – Fluxo alternativo 2 (FN_-2) - Remover
"""""""""""""""""""""""""""""""""""""""""""

#. O ator seleciona a opção ``Remover`` de uma das linhas da listagem de anexos já cadastrados
#. O sistema apresenta a listagem do passo FN-2

FA3 – Fluxo alternativo 3 (FN_-2) - Anexar arquivo
""""""""""""""""""""""""""""""""""""""""""""""""""

#. O ator seleciona a opção ``Anexar arquivo`` de uma das linhas da listagem de anexos já cadastrados
#. Na tela ``Anexar arquivo`` o ator escolhe o arquivo a anexar
#. O ator seleciona a opção ``Salvar``
#. O sistema apresenta a listagem do passo FN-2

.. note::

  Se possível anexar já ao incluir/editar.

Fluxo de Exceção
^^^^^^^^^^^^^^^^

Não há.


Especificação suplementares
---------------------------

Requisitos Não-Funcionais
^^^^^^^^^^^^^^^^^^^^^^^^^

Não há.


Requisitos de Interface
^^^^^^^^^^^^^^^^^^^^^^^

Não há.


Requisitos de Informação
^^^^^^^^^^^^^^^^^^^^^^^^

.. _RIN01:

RIN01 – Campos para listagem de anexos do edital
""""""""""""""""""""""""""""""""""""""""""""""""

.. list-table:: 
   :header-rows: 1
   :stub-columns: 1

   * - 
     - Nome 
     - Descrição
     - Arquivo Digitalizado
     - Ações
   * - Ordenação
     - Sim (padrão, ascendente)
     - Não
     - Não
     - Não
   * - Observações
     - 
     - 
     - 
     - 
       .. csv-table::
          :header: "Rótulo"
          :widths: 100

          Editar
          Remover
          Anexar arquivo



.. _RIN02:

RIN02 – Campos para cadastros de editais (incluir e editar)
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

.. list-table:: 
   :header-rows: 1
   :stub-columns: 0

   * - Informação
     - Tipo
     - Tamanho
     - Valor Inicial
     - Domínio
     - Máscara
   * - Nome*
     - Texto
     - 255
     - 
     - 
     - 
   * - Descrição*
     - Texto Longo
     - 
     - 
     - 
     - 


     
Regras de Negócio
^^^^^^^^^^^^^^^^^
Não há.
  
.. comment:

  .. list-table:: 
     :widths: 10 90
     :header-rows: 1
     :stub-columns: 0

     * - Regra
       - Descrição / Mensagem
     * - RN1
       - | Nome da regra
         | Mensagem 
   
Mensagens
^^^^^^^^^

Não há.

.. comment:
  .. _M:

  .. list-table:: 
     :widths: 10 90
     :header-rows: 1
     :stub-columns: 0

     * - Código
       - Descrição
     * - M1    
       - 

  .. _M1: `Mensagens`_     
     
Ponto de Extensão
-----------------

Não há.


Questões em Aberto
------------------

Não há.


Esboço de Protótipo 
-------------------

Não há.


Diagrama de domínio do caso de uso
----------------------------------

Não há.


Diagrama de Fluxo de Operação
-----------------------------

Não há.


Cenário de Testes
-----------------
.. note::
    Documentar.

.. comment:
  Objetivos
  ^^^^^^^^^

  O objetivo desde Caso de Testes é identificar o maior número possível de cenários e variações dos requisitos 
  de software desde Caso de Uso. É dado um conjunto de dados de entradas, condições de execução, resultados 
  esperados que visam validar esse caso de uso.

  Casos e Registros de Teste
  ^^^^^^^^^^^^^^^^^^^^^^^^^^

  Fluxo de Exceção FE1
  """"""""""""""""""""

  .. list-table:: 
     :widths: 10 50
     :stub-columns: 1

     * - Objetivo
       - 
     * - Dados de Entrada
       - 
     * - Resultado Esperado
       - 
       
