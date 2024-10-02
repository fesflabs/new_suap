
.. |logo| image:: ../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Progressão Funcional** 

.. include:: ../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-rh-progressoes-uc04:

UC 04 - Calcular média de avaliação <v0.1>
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
   * - 19/02/2014
     - 0.1
     - Início do Documento     
     - Esdras Valentim    



Objetivo
--------

Esse caso de uso calcula a média de avaliação do servidor (com ou sem função).

Atores
------

- Servidor
- SUAP
  

Principais
^^^^^^^^^^

- SUAP

Interessado
^^^^^^^^^^^

- Servidor

Pré-condições
-------------

O formulário de avaliação deve ser preenchido e salvo pelo servidor avaliador

Pós-condições
-------------

- A nota é calculada e persistida

Fluxo de Eventos
----------------
- O caso de uso é iniciado quando o servidor salva o fomulário de avaliação

Fluxo Normal
^^^^^^^^^^^^

- O servidor seleciona a opção enviar avaliação
- O sistema calacula a média de avaliação do servidor avaliado  


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

- Para os servidores sem função administrativa, a nota do chefe e a média da equipe serão consideradas igual a zero até que seja 
  lançada a primeira nota. Fórmula: ``MAD = (AUTO*1 + CHEFE*1 + MEquipe*2)/4``.

- Para servidores com função administrativa, a nota do chefe e a média dos pares serão consideradas zero até que seja lançada a \
  primeira nota. Fórmula: ``MAD = (AUTO*1 + CHEFE*1 + MPares*2)/4``.


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

- A média será persistida ou calculada em tempo de execução?

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
