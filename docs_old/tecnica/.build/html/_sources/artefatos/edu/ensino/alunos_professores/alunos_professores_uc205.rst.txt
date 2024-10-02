
.. |logo| image:: ../../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Ensino** 

.. include:: ../../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-edu-ensino-alunos_professores-uc205: 

UC 205 - Cancelar Matrícula <v0.1>
==================================

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

O usuário poderá cancelar a matrícula do aluno indefinidamente.

Atores
------

Principais
^^^^^^^^^^

Administrador do sistema, Diretor Acadêmico e Secretário: podem cancelar a matrícula do aluno.

Interessado
^^^^^^^^^^^

Aluno.

Pré-condições
-------------

O aluno deve estar com a matrícula ativa (matriculado, concludente ou em aberto).

Pós-condições
-------------

O Aluno, os diários do aluno, e a situação da matrícula do aluno no período corrente devem ficar com a matrícula institucional cancelada
com o respectivo motivo.

Casos de Uso Impactados
-----------------------

	#. :ref:`suap-artefatos-edu-ensino-alunos_professores-uc202` - Adiciona o botão de Cancelamento de matrícula e altera a situação do 
	   aluno e do período corrente do aluno para cancelado, além de exibir na aba de procedimentos realizados o cancelamento
	   na situação do aluno.
	#. :ref:`suap-artefatos-edu-ensino-diarios-uc402` - Altera a situação do aluno no diário para cancelado.
	#. :ref:`suap-artefatos-edu-ensino-diarios-uc400` - Altera a situação do aluno no diário para cancelado.

Fluxo de Eventos
----------------

Fluxo Normal
^^^^^^^^^^^^

.. _FN:

    #. O caso de uso é iniciado acionando a opção  ``ENSINO`` > ``Alunos e Professores`` > ``Aluno``
    #. O sistema exibe a lista de alunos (:ref:`suap-artefatos-edu-ensino-alunos_professores-uc202-RIN1`)
    #. O Administrador do sistema, Diretor Acadêmico e Secretário visualiza o aluno ativo.
    #. O sistema exibe as informações sobre o aluno (:ref:`suap-artefatos-edu-ensino-alunos_professores-uc202-RI1`).
    #. O Administrador do sistema, Diretor Acadêmico e Secretário seleciona a opção ``Ações`` > ``Cancelar Matrícula``
    #. O sistema exibe o formulário de cancelamento de matrícula (RIN1_).
    #. O Administrador do sistema, Diretor Acadêmico e Secretário informa os dados e finaliza o caso de uso selecionando a opção ``Salvar``
    #. O sistema exibe a mensagem M1_ e apresenta a listagem do passo FN_.2 


Fluxo Alternativo
^^^^^^^^^^^^^^^^^

Não há.
    	
Fluxo de Exceção
^^^^^^^^^^^^^^^^

FE1 – Cancelamento fere Regra RN4_ (FN_.7)
""""""""""""""""""""""""""""""""""""""""""

	#. O sistema exibe a mensagem M2_.

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

.. _RIN1:

RIN1 – Campos para Cadastros
""""""""""""""""""""""""""""

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
     - 
     - 
   * - Período Letivo Atual*
     - Texto (Rótulo)
     - 
     - Último período aberto do aluno
     - 
     - 
   * - Aluno*
     - Texto (Rótulo)
     - 
     - Nome do aluno e matrícula
     - 
     - 
   * - Motivo*
     - Combobox
     - 
     - Cancelamento Compulsório
     - #. Cancelamento Compulsório
       #. Cancelamento voluntário
       #. Evasão
       #. Jubilamento
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
A `Figura 2`_ exibe um esboço do formulário de cancelamento de matrícula.

     
Regras de Negócio
^^^^^^^^^^^^^^^^^

.. list-table:: 
   :widths: 10 90
   :header-rows: 1
   :stub-columns: 0

   * - Regra
     - Descrição / Mensagem
   * - RN1
     - O sistema deve exibir a opção ``Ações`` > ``Cancelar Matrícula`` somente quando a matrícula do aluno estiver em 
       condições de ser cancelada (RN4_). Caso contrário a opção deve estar visível mas desabilitada.
   * - RN2
     - O sistema deve manter todo o histórico acadêmico do aluno (disciplinas, notas, faltas, etc).
   * - RN3
     - O sistema deve alterar a situação do aluno nos diários abertos para cancelado e não deve permitir mais alterações, inserções 
       e exclusões no mesmo.
   * - RN4
     - O sistema só deve permitir o cancelamento de matrículas em ano/períodos não fechados, ou seja o aluno deve estar **matriculado, 
       concludente ou em aberto (renovação)** no último ano/período letivo do aluno;
   
  
.. _RN1: `Regras de Negócio`_  
.. _RN2: `Regras de Negócio`_  
.. _RN3: `Regras de Negócio`_  
.. _RN4: `Regras de Negócio`_  
   
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
     - Cancelamento de matrícula realizado com sucesso.
   * - M2
     - Impossível cancelar matrícula de <campo aluno>.

.. _M1: `Mensagens`_     
.. _M2: `Mensagens`_

    
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

.. figure:: media/tela_uc205_01.png
   :align: center
   :scale: 100 %
   :alt: protótipo de tela.
   :figclass: align-center
   
   Figura 1: Protótipo de tela para visualização do aluno.
	   
	   
.. _`Figura 2`:

.. comentário para usar o exemplo abaixo, basta recuar a margem.
	   
.. figure:: media/tela_uc205_02.png
   :align: center
   :scale: 70 %
   :alt: protótipo de tela.
   :figclass: align-center
   
   Figura 2: Protótipo de tela para cancelamento de matrícula de alunos.	   

Diagrama de domínio do caso de uso
----------------------------------

Não há.

Diagrama de Fluxo de Operação
-----------------------------

Não há.

Cenário de Testes
-----------------

Não há.