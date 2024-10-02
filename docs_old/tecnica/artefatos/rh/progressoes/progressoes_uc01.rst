
.. |logo| image:: ../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Progressão Funcional** 

.. include:: ../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-rh-progressoes-uc01:

UC 01 - Selecionar avaliadores <v0.1>
=====================================

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
   * - 14/07/2014
     - 0.1
     - Início do Documento
     - Esdras Valentim e George Carvalho
    

Objetivo
--------
Esse caso de uso descreve como o RH selecionará avaliadores que preencherão o formulário de avaliação de desempenho do servidor. 

Atores
------

- RH 
- SUAP

Principais
^^^^^^^^^^

- RH

Interessado
^^^^^^^^^^^

- Servidor

Pré-condições
-------------

- Iniciar processo

Pós-condições
-------------

Será criado uma lista de avaliadores. 

Fluxo de Eventos
----------------

- O RH seleciona o processo de progressão
- O RH inicia o caso de uso acionando a pesquisa de servidores por setor
- O RH seleciona os servidores/avaliadores 
- O RH insere os servidores localizados numa lista de avaliadores
- O RH finaliza o caso de uso acionando a opção salvar.
- O sistema envia uma mensagem para os avaliadores selecionados, indicando que há avaliações pendentes.

Fluxo Normal
^^^^^^^^^^^^

.. _FN:
    
    #. O caso de uso é iniciado acionando a opção  ``RECURSOS HUMANOS`` > ``Progressões`` > ``Técnico`` > ``Iniciar processo``
    #. O sistema exibe a lista de servidores por setor
   


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
- O sistema deve verificar o tempo mínimo de trabalho entre os avaliadores e avaliado como pré-condição para avaliar.


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

.. _PE:
     
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
