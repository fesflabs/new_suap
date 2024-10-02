
.. |logo| image:: ../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Progressão Funcional** 

.. include:: ../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-rh-progressoes-uc02:

UC 02 - Obter servidores a progredir <v0.1>
===========================================

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
   * - 15/07/2014
     - 0.1
     - Início do Documento
     - Esdras Valentim e George Carvalho
    


Objetivo
--------
Esse caso de uso descreve a ação de mostrar todos os servidores que estão aptos a progredir.

Atores
------

- SUAP  

Principais
^^^^^^^^^^

- SUAP

Interessado
^^^^^^^^^^^

- RH

Pré-condições
-------------

- Servidor faltando 45 dias para 18 meses de efetivo exercício ou 120 para o final do estágio probatório

Pós-condições
-------------

- É mostrado uma lista de servidores aptos a progredir na tela

Fluxo de Eventos
----------------

- O RH entra na tela inicial do suap
- O sistema mostra a lista de servidores aptos a progredir

Fluxo Normal
^^^^^^^^^^^^

.. _FN:

    #. O caso de uso é iniciado acionando a opção  ``INÍCIO``
    #. O sistema exibe a lista de servidores aptos a progredir    


Fluxo Alternativo
^^^^^^^^^^^^^^^^^

``Não se aplica``


FA1 – Nome do fluxo alternativo (FN_.1)
"""""""""""""""""""""""""""""""""""""""

``Não se aplica``
    

Fluxo de Exceção
^^^^^^^^^^^^^^^^

``Não se aplica``
    
FE1 – Nome do fluxo de exceção (FN_.2)
""""""""""""""""""""""""""""""""""""""

``Não se aplica``

Especificação suplementares
---------------------------

- Os afastamentos devem ser descontados do cálculo do tempo que definirá os servidores aptos a progredir


Requisitos Não-Funcionais
^^^^^^^^^^^^^^^^^^^^^^^^^

``Não se aplica``
    

Requisitos de Interface
^^^^^^^^^^^^^^^^^^^^^^^

``Não se aplica``


Requisitos de Informação
^^^^^^^^^^^^^^^^^^^^^^^^

.. _RIN1:

RIN1 – Campos para listagem
"""""""""""""""""""""""""""

.. list-table:: 
   :header-rows: 1
   :stub-columns: 1

   * - 
     - Ações
     - Coluna 1
     - Coluna 2
   * - Ordenação
     - Não
     - Sim
     - Não
   * - Filtro
     - Não
     - Não
     - Sim
   * - Busca
     - Não
     - Sim
     - Não   
   * - Observações
     - 
       .. csv-table::
          :header: "Rótulo"
          :widths: 100

          Ver
          Editar
     - 
     -   

.. _RIN2:

RIN2 – Campos para Cadastros
""""""""""""""""""""""""""""

``Não se aplica``
          
Regras de Negócio
^^^^^^^^^^^^^^^^^

``Não se aplica``
   
Mensagens
^^^^^^^^^

``Não se aplica``
     
Ponto de Extensão
-----------------

``Não se aplica``

Questões em Aberto
------------------

- Quais os afastamentos que serão descontados?

Esboço de Protótipo
-------------------

``Não se aplica``

Diagrama de domínio do caso de uso
----------------------------------

``Não se aplica``

Diagrama de Fluxo de Operação
-----------------------------

``Não se aplica``

Cenário de Testes
-----------------

Objetivos
^^^^^^^^^

O objetivo desde Caso de Testes é identificar o maior número possível de cenários e variações dos requisitos 
de software desde Caso de Uso. É dado um conjunto de dados de entradas, condições de execução, resultados 
esperados que visam validar esse caso de uso.

Casos e Registros de Teste
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::   
    Identifique (Tipo de Teste) se o teste é relativo a um fluxo alternativo, de exceção, regra de negócio, 
    permissão.

Fluxo de Exceção FE1
""""""""""""""""""""

.. list-table:: 
   :widths: 10 50
   :stub-columns: 1

   * - Objetivo
     - Texto com o objetivo do teste
   * - Dados de Entrada
     - Texto descrevendo os dados de entrada
   * - Resultado Esperado
     - Texto descrevendo o resultado esperado.
