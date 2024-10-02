
.. |logo| image:: ../../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Ensino** 

.. include:: ../../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-edu-ensino-alunos_professores-uc206: 

UC 206 - Reintegrar Matrícula <v0.1>
====================================

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
   * - 16/05/2014
     - 0.1
     - Início do Documento
     - Hugo Tácito Azevedo de Sena

Objetivo
--------

O usuário poderá reintegrar uma matrícula cancelada de um aluno, registrando o retorno de um aluno ao curso em um novo período.

Atores
------

Principais
^^^^^^^^^^

Administrador do sistema, Diretor Acadêmico e Secretário: podem reintegrar um cancelamento sobre a matrícula do aluno.

Interessado
^^^^^^^^^^^

Aluno.

Pré-condições
-------------

	#. O aluno está com a matrícula cancelada (por evasão, cancelamento voluntário/compulsório, jubilamento e transferências
	   externa/interna).

Pós-condições
-------------

	#. Aluno fica com a situação da matrícula reintegrada (situação do período **em aberto**, situação da matrícula igual a
	   situação anterior ao cancelamento e nenhuma mudança nos diários).

Casos de Uso Impactados
-----------------------

	#. :ref:`suap-artefatos-edu-ensino-alunos_professores-uc202` - Adiciona o botão de ``Reintegrar matrícula`` e altera a situação do 
	   matrícula do aluno para em aberto, e a situação do período do aluno para o estado anterior ao cancelamento. Além de exibir na aba 
	   de procedimentos realizados a nova situação do período do aluno.

Fluxo de Eventos
----------------

Fluxo Normal
^^^^^^^^^^^^

.. _FN:

    #. O caso de uso é iniciado acionando a opção  ``ENSINO`` > ``Alunos e Professores`` > ``Aluno``
    #. O sistema exibe a lista de alunos (:ref:`suap-artefatos-edu-ensino-alunos_professores-uc202-RIN1`)
    #. O Administrador do sistema, Diretor Acadêmico e Secretário visualiza o aluno cancelado.
    #. O sistema exibe as informações sobre o aluno (:ref:`suap-artefatos-edu-ensino-alunos_professores-uc202-RI1`).
    #. O Administrador do sistema, Diretor Acadêmico e Secretário seleciona a opção ``Ações`` > ``Reintegrar Aluno``
    #. O sistema exibe o formulário de reintegração de matrícula (RIN1_).
    #. O Administrador do sistema, Diretor Acadêmico e Secretário informa os dados e finaliza o caso de uso selecionando a opção ``Salvar``
    #. O sistema exibe a mensagem M1_ e apresenta a listagem do passo FN_.2

Fluxo Alternativo
^^^^^^^^^^^^^^^^^

Não há.    	
    	
Fluxo de Exceção
^^^^^^^^^^^^^^^^

FE1 – Cancelamento fere Regra RN3_ (FN_.7)
""""""""""""""""""""""""""""""""""""""""""

	#. O sistema exibe a mensagem M2_.

FE2 – Reintegração fere Regra RN4_ (FN_.7)
""""""""""""""""""""""""""""""""""""""""""

	#. O sistema exibe a mensagem M3_.

Especificação suplementares
---------------------------

Requisitos Não-Funcionais
^^^^^^^^^^^^^^^^^^^^^^^^^ 

Não há.

Requisitos de Interface
^^^^^^^^^^^^^^^^^^^^^^^

Não há

Requisitos de Informação
^^^^^^^^^^^^^^^^^^^^^^^^

.. _RIN1:

RIN1 – Campos para Reintegração
"""""""""""""""""""""""""""""""

.. list-table:: 
   :widths: 10 5 5 10 10 10
   :header-rows: 1
   :stub-columns: 0

   * - Informação
     - Tipo
     - Tamanho
     - Valor Inicial
     - Domínio/Máscara
     - Observação
   * - Ano Letivo Atual*
     - Texto (Rótulo)
     - 
     - Último ano aberto do aluno
     - Ano letivo
     - 
   * - Período Letivo Atual*
     - Texto (Rótulo)
     - 
     - Último período aberto do aluno
     - Período letivo
     - 
   * - Aluno*
     - Texto (Rótulo)
     - 
     - Nome do aluno e matrícula
     - 
     - 
   * - Processo*
     - Texto
     - 
     - 
     - Processo
     - Autocompletar
   * - Observações*
     - Texto
     - 
     - 
     - 
     - 
   * - Ano Letivo da Reintegração*
     - Combobox
     - 
     - Ano corrente
     - Ano letivo
     - 
   * - Período Letivo da Reintegração*
     - Combobox
     - 
     - Período corrente
     - Período letivo
     - 
   * - Data*
     - Texto (Rótulo)
     - 
     - Dia corrente
     - 
     - 
   * - Secretário*
     - Oculto
     - 
     - 
     - Servidor
     - 
A `Figura 2`_ exibe um esboço do formulário de reintegração de matrícula.

     
Regras de Negócio
^^^^^^^^^^^^^^^^^

.. list-table:: 
   :widths: 10 90
   :header-rows: 1
   :stub-columns: 0

   * - Regra
     - Descrição / Mensagem
   * - RN1
     - O procedimento de reintegração deve restaurar o estado da situação da matrícula do aluno 
       para o estado no qual ele se encontrava anteriormente ao procedimento de cancelamento/trancamento.
   * - RN2
     - A reintegração deve gerar o período solicitado com a situação ``em aberto``
   * - RN3
     - O sistema só deve permitir a reintegração para alunos que estão com a matrícula cancelada.
   * - RN4
     - O sistema não deve permitir a reintegração de matrícula no mesmo período em que foi feito o cancelamento, 
       somente em períodos posteriores.
   * - RN5
     - Se o aluno conseguir retornar no mesmo período do cancelamento, este deve solicitar o cancelamento de procedimento 
       (:ref:`suap-artefatos-edu-ensino-alunos_professores-uc204-FA1`).
   * - RN6
     - O botão de reintegração de matrícula só está habilitado quando o aluno está com situação de matrícula cancelada.
     
.. _RN1: `Regras de Negócio`_  
.. _RN2: `Regras de Negócio`_  
.. _RN3: `Regras de Negócio`_  
.. _RN4: `Regras de Negócio`_  
.. _RN5: `Regras de Negócio`_
.. _RN6: `Regras de Negócio`_

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
     - Aluno reintegrado com sucesso.
   * - M2
     - Impossível reintegrar aluno.  
   * - M3
     - Período de reintegração inválido. 

.. _M1: `Mensagens`_     
.. _M2: `Mensagens`_
.. _M3: `Mensagens`_    
.. _M4: `Mensagens`_    
.. _M5: `Mensagens`_
.. _M6: `Mensagens`_

    
.. _PE:

Ponto de Extensão
-----------------

Não há.

Questões em Aberto
------------------

Não há.

Esboço de Protótipo
-------------------

.. _`Figura 1`:

.. comentário para usar o exemplo abaixo, basta recuar a margem.

.. figure:: media/tela_uc206_01.png
   :align: center
   :scale: 100 %
   :alt: protótipo de tela.
   :figclass: align-center
   
   Figura 1: Protótipo de tela para exibição de procedimentos de matrícula.

.. _`Figura 2`:

.. comentário para usar o exemplo abaixo, basta recuar a margem.

.. figure:: media/tela_uc206_02.png
   :align: center
   :scale: 100 %
   :alt: protótipo de tela.
   :figclass: align-center
   
   Figura 2: Protótipo de tela para visualização do aluno.

Diagrama de domínio do caso de uso
----------------------------------

Não há.

Diagrama de Fluxo de Operação
-----------------------------

Não há.

Cenário de Testes
-----------------

Não há.