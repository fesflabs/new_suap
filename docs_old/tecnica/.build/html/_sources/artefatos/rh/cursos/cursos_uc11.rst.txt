
.. |logo| image:: ../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Cursos** 

.. include:: ../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-rh-cursos-uc11:

UC 11 - Ver relatório de horas trabalhadas <v0.1>
=================================================

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
   * - 29/03/2014
     - 0.1
     - Início do Documento
     - 

Objetivo
--------


Atores
------


Principais
^^^^^^^^^^

Interessado
^^^^^^^^^^^

Pré-condições
-------------


Pós-condições
-------------


Fluxo de Eventos
----------------


Fluxo Normal
^^^^^^^^^^^^
.. _FN:

    #. O caso de uso é iniciado acionando a opção “ ” (RI1_)
    #. ...  

Fluxo Alternativo
^^^^^^^^^^^^^^^^^

FA1 – Fluxo alternativo 1 (FN_-1)
""""""""""""""""""""""""""""""""""

Fluxo de Exceção
^^^^^^^^^^^^^^^^

FE1 – Exclusão fere Regra RN1 [FN_-2)
""""""""""""""""""""""""""""""""""""""

Especificação suplementares
---------------------------

Requisitos Não-Funcionais
^^^^^^^^^^^^^^^^^^^^^^^^^ 

RNF1 – Tempo de Resposta
""""""""""""""""""""""""

Requisitos de Interface
^^^^^^^^^^^^^^^^^^^^^^^

.. _RI1:

[RI1] – Acesso à opção “ ”
""""""""""""""""""""""""""

Menu " " > " " > " "

Requisitos de Informação
^^^^^^^^^^^^^^^^^^^^^^^^

RIN – Campos para Cadastros
"""""""""""""""""""""""""""

.. list-table:: 
   :widths: 10 20 5 5 5 5
   :header-rows: 1
   :stub-columns: 0

   * - Informação
     - Tipo
     - Tamanho
     - Valor Inicial
     - Domínio
     - Máscara
   * - ex Prédio
     - | Seleção 
       | (ComboBox)
     - 
     - 
     - 
     - 
   * - ex Setores*
     - | Texto 
       | (Busca Interativa)
     - 
     - 
     - 
     - 
     
Regras de Negócio
^^^^^^^^^^^^^^^^^

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

Questões em Aberto
------------------

Esboço de Protótipo 
-------------------

Diagrama de domínio do caso de uso
----------------------------------

Diagrama de Fluxo de Operação
-----------------------------

Cenário de Testes
-----------------

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