
.. |logo| image:: ../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Progressão Funcional** 

.. include:: ../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-rh-progressoes-uc05:

UC 05 - Iniciar Processo <v0.1>
===============================

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
   * - 17/07/2014
     - 0.1
     - Início do Documento
     - George Carvalho
    
Objetivo
--------

Descreve a abertura do processo de progressão.

Atores
------

- RH 

Principais
^^^^^^^^^^

- RH

Interessado
^^^^^^^^^^^

- Servidor

Pré-condições
-------------
- Servidores aptos a progredir


Pós-condições
-------------

Processo de abertura de progressão

Fluxo de Eventos
----------------
- O caso de uso se inicia quando o RH seleciona a opção: processo de progressão
- O RH seleciona o servidor dentre os aptos a progredir
- O RH aciona o caso de uso selecionar avaliadores :ref:`suap-artefatos-rh-progressoes-uc01`  

Fluxo Normal
^^^^^^^^^^^^

.. _FN:

    #. O caso de uso é iniciado acionando a opção  ``RECURSOS HUMANOS`` > ``Progressões`` > ``Técnico`` > ``Iniciar processo``
    #. O RH seleciona o servidor a progredir
    #. O RH aciona o caso de uso selecionar avaliadores
   

Fluxo Alternativo
^^^^^^^^^^^^^^^^^

FA1 – Editar processo (FN_.1)
"""""""""""""""""""""""""""""
    
    FA1 – Editar processo (FN_.2 )
    """""""""""""""""""""

      #. O RH aciona a opção ``RECURSOS HUMANOS`` > ``Progressões`` > ``Técnico`` > ``Editar processo` 
      #. O RH gerencia a lista de avaliadores
      #. O RH finaliza o caso de uso selecionando a opção ``Alterar``     
   

Fluxo de Exceção
^^^^^^^^^^^^^^^^

``Não se aplica``
    
FE1 – Nome do fluxo de exceção (FN_.2)
""""""""""""""""""""""""""""""""""""""

``Não se aplica``

Especificação suplementares
---------------------------

``Não se aplica``

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

``Não se aplica``

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

``Não se aplica``

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
