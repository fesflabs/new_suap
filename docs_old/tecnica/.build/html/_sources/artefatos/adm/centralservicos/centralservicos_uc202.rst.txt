.. include:: header.rst

.. _suap-artefatos-adm-centralservicos-uc202:

UC202 - Listar e Autorizar Chamados <v0.1>
==========================================

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
   * - 07/07/2014
     - 0.1
     - Início do Documento
     - Rafael Pinto

Objetivo
--------

.. _suap-artefatos-adm-centralservicos-uc202-objetivo:

Listar chamados e possibilitar autorização dos mesmos, para chamados de sua competência.


Atores
------

Principais
^^^^^^^^^^
Autorizador

Interessado
^^^^^^^^^^^



Pré-condições
-------------
Chamado cadastrado.


Pós-condições
-------------


Fluxo de Eventos
----------------


Fluxo Normal
^^^^^^^^^^^^
.. _FN:

    #. O caso de uso é iniciado selecionando a opção ``Central de Serviços`` > ``Autorização``
    #. O sistema apresenta uma listagem dos chamados abertos que o usuário logado seja responsável pela autorização (RIN01_):
    #. O ator clica no icone de ``Seleção do Chamado`` (primeira coluna da listagem), selecionando os chamados que deseja autorizar
    #. O ator clica no botão ``Autorizar``
    #. O sistema apresenta a listagem do passo FN-2


Fluxos de Exceção
^^^^^^^^^^^^^^^^^

    #. O caso de uso é iniciado selecionando a opção ``Central de Serviços`` > ``Autorização``
    #. O sistema apresenta uma listagem dos chamados abertos que o usuário logado seja responsável pela autorização (RIN01_):
    #. O ator seleciona a opção ``Visualizar Chamado``
    #. O ator clica no botão ``Autorizar``
    #. O sistema apresenta a listagem do passo FN-2

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


RIN01 – Campos para listagem de chamados
""""""""""""""""""""""""""""""""""""""""

.. list-table:: 
   :header-rows: 1
   :stub-columns: 1

   * - 
     - Opções
     - Serviço
     - Em nome de
     - Requisitante
     - Aberto em
   * - Ordenação
     - Não
     - Sim
     - Sim
     - Sim
     - Sim
   * - Filtro
     - Não
     - Não
     - Não
     - Não
     - Não
   * - Busca
     - Não
     - Não
     - Não
     - Não
     - Não
   * - Observações
     - 
       .. csv-table::
          :header: "Rótulo"
          :widths: 100

          Visualizar
          Selecionar

     - 
     - 
     - 
     -
	 
.. _RIN02:

RIN02 – Campos para visualização do chamado
"""""""""""""""""""""""""""""""""""""""""""

.. list-table:: 
   :header-rows: 1
   :stub-columns: 0

   * - Informação
     - Tipo
     - Tamanho
     - Valor Inicial
     - Domínio
     - Máscara
   * - Serviço
     - Seleção (desabilitado)
     - 
     - 
     -  
     - 
   * - Em nome de
     - Texto (Desabilitado)
     - 
     - 
     - 
     -     
   * - Requisitante
     - Texto (Desabilitado)
     - 
     - 
     - 
     -      
   * - Descrição do chamado
     - Texto Longo (Desabilitado)
     - 
     - 
     -  
     - 
   * - Data/Hora de Abertura
     - Data/Hora (Desabilitado)
     - 
     - 
     - 
     -
   * - Status
     - Seleção (Desabilitado)
     - 
     - 
     - 
     -

Regras de Negócio
^^^^^^^^^^^^^^^^^

Não há.
   

Mensagens
^^^^^^^^^

Não há.
  

.. _pde:

Ponto de Extensão
-----------------

Não há.


Questões em Aberto
------------------

Não há.

Esboço de Protótipo 
-------------------

Tela de listagem e autorização de chamado de usuário
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. image:: imagens/tela-listagem-e-autorizacao-chamado-usuario.png

Tela de autorização de chamado de usuário
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. image:: imagens/tela-autorizacao-chamado-usuario.png

Diagrama de domínio do caso de uso
----------------------------------

Não há.


Diagrama de Fluxo de Operação
-----------------------------

Não há.


Cenário de Testes
-----------------

.. note:: Falta construir os cenários de teste.

.. comment

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
     
