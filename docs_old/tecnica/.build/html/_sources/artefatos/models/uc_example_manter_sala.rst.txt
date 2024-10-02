
.. |logo| image:: ../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Comum** 

.. include:: ../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-adm-comum-uc01:

UC 01 - Manter Sala <v0.1>
==========================

Especialista do :ref:`Caso de Uso Abstrado CRUD <suap-modelos-uccrudabstract>`

.. sectnum::
    :depth: 4
    :suffix: .

.. contents:: Conteúdo
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
   * - 18/02/2014
     - 0.1
     - Início do Documento
     - 

Objetivo
--------

Este caso de uso possibilita que um usuário cadastre, liste ou altere uma sala. 

Atores
------

Principais
^^^^^^^^^^

**Operador de Chave (chaves_operador)**: responsável por manter o cadastro de salas.

**Gerente do Patrimônio (patrimonio_gerente_sistemico)**: tem as mesmas atribuições do Operador de Chave.

Interessado
^^^^^^^^^^^

Não há.

Pré-condições
-------------

Pós-condições
-------------

Não há.

Fluxo de Eventos
----------------

Fluxo Normal
^^^^^^^^^^^^

Fluxo Alternativo
^^^^^^^^^^^^^^^^^

Fluxo de Exceção
^^^^^^^^^^^^^^^^

Especificação suplementares
---------------------------

Requisitos Não-Funcionais
^^^^^^^^^^^^^^^^^^^^^^^^^ 

Não há.

Requisitos de Interface
^^^^^^^^^^^^^^^^^^^^^^^

.. _RI1:

RI1 – Acesso ao caso de uso
"""""""""""""""""""""""""""

Menu ADMINISTRAÇÃO > Cadastros > Salas

RI2 – Acesso a opção Cadastrar
""""""""""""""""""""""""""""""

O acesso a opção será efetuado a partir do botão "Adicionar Sala"

Requisitos de Informação
^^^^^^^^^^^^^^^^^^^^^^^^

RIN1 – Listagem – critério de exibição, ordenação e filtro
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

	1. Campos para exibição
		"Nome", "Prédio", "Setores", "Ativa", "Agendável"
	2. Campos para ordenação
		"Nome"
	3. Campos para filtro
		"Nome", "Campus" (predio)

RIN2 – Campos para Cadastros
""""""""""""""""""""""""""""

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
   * - Nome*
     - Texto
     - 100
     - 
     - 
     - 
   * - Ativa
     - Boolean
     - 
     - 
     - 
     - 
   * - Predio*
     - | Seleção 
       | (Combo Box)
     - 
     - 
     - 
     - 
   * - Setores
     - | Texto
       | (Busca Interativa)
     - 
     - 
     - 
     - 
   * - Agendavel
     - Boolean
     - 
     - 
     - 
     - 
   * - Capacidade
     - Texto 
     - 
     - 
     - Numérico
     - 
   * - Avaliadores
     - | Texto
       | (Busca Interativa)
     - 
     - 
     - 
     - 
     
RIN3 – Campos para Cadastros
""""""""""""""""""""""""""""

Os mesmos definidos em RIN2_

.. _RIN2: `RIN2 – Campos para Cadastros`_
                              

RIN4 – Campos para validar cadastro em duplicidade
"""""""""""""""""""""""""""""""""""""""""""""""""""

"Nome", "Prédio"
     
Regras de Negócio
^^^^^^^^^^^^^^^^^

.. list-table:: 
   :widths: 10 90
   :header-rows: 1
   :stub-columns: 0

   * - Regra
     - Descrição / Mensagem
   * - 
     - 
   
Mensagens
^^^^^^^^^

.. _M:

.. list-table:: 
   :widths: 10 90
   :header-rows: 1
   :stub-columns: 0

   * - Código
     - Descrição
   * - M3    
     - Sala com este Nome e Prédio já existe.

.. _M1: `Mensagens`_     
     
Ponto de Extensão
-----------------

Não há.

Questões em Aberto
------------------

Não há.

Esboço de Protótipo 
-------------------

Não se aplica.

Diagrama de domínio do caso de uso
----------------------------------

.. image:: diagrama_dominio.jpg

Diagrama de Fluxo de Operação
-----------------------------

Não há.

Cenário de Testes
-----------------

Objetivos
^^^^^^^^^

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
