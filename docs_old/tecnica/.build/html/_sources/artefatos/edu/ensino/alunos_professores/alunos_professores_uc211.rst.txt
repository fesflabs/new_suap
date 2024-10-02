
.. |logo| image:: ../../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Ensino** 

.. include:: ../../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-edu-ensino-alunos_professores-uc211: 

UC 211 - Editar Dados Funcionais do Professor <v0.1>
====================================================

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
   * - 22/05/2014
     - 0.1
     - Início do Documento
     - Hugo Sena

Objetivo
--------

Permite editar o núcleo central estruturante e matéria disciplina do professor.

Atores
------

Principais
^^^^^^^^^^

Administrador: pode editar os dados.

Interessado
^^^^^^^^^^^

Não se aplica.

Pré-condições
-------------

Professor cadastrado.

Pós-condições
-------------

Dados funcionais do professor atualizados.

Casos de Uso Impactados
-----------------------

	#. :ref:`suap-artefatos-edu-ensino-alunos_professores-uc208` - Adiciona o botão para editar alguns dados funcionais do professor
	#. :ref:`suap-artefatos-edu-ensino-cad_gerais-uc121` - Define as opções de tipos de matéria disciplina 
	#. :ref:`suap-artefatos-edu-ensino-cad_gerais-uc122` - Define as opções de tipos de NCE

Fluxo de Eventos
----------------

Fluxo Normal
^^^^^^^^^^^^

.. _FN:

    #. O caso de uso é iniciado acionando a opção  ``ENSINO`` > ``Alunos e Professores`` > ``Professores``
    #. O sistema exibe a lista de professores (:ref:`suap-artefatos-edu-ensino-alunos_professores-uc208-RIN1`)
    #. O Administrador seleciona um professor.
    #. O sistema exibe os dados gerais do professor.
    #. O Administrador seleciona a aba ``Dados Funcionais``.
    #. O sistema exibe os dados funcionais do professor.
    #. O Administrador seleciona a opção ``Editar Matéria Disciplina/NCE``
    #. O sistema exibe um formulário de edição de matéria disciplina e NCE.
    #. O Administrador informa os dados (RIN2_)
    #. O Administrador finaliza o caso de uso selecionando a opção ``Salvar``
    #. O sistema exibe a mensagem M1_
    #. O sistema apresenta a listagem do passo FN_.2 


Fluxo Alternativo
^^^^^^^^^^^^^^^^^

Não há.
    	
    	
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

.. _RIN1:
     
RIN1 – Campos para edição de dados funcionais do professor
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
 

.. list-table:: 
   :widths: 10 10 5 5 15 5
   :header-rows: 1
   :stub-columns: 0

   * - Informação
     - Tipo
     - Tamanho
     - Valor Inicial
     - Domínio/Máscara
     - Observação
   * - Matéria Disciplina*
     - ComboBox
     - 
     - 
     - Matéria Disciplina
     - 
   * - NCE*
     - ComboBox
     - 
     - 
     - NCE
     - 

A `Figura 1`_ exibe um esboço do formulário de edição.

     
Regras de Negócio
^^^^^^^^^^^^^^^^^

.. list-table:: 
   :widths: 10 90
   :header-rows: 1
   :stub-columns: 0

   * - Regra
     - Descrição / Mensagem
   * - RN1
     - Somente o administrador pode editar os dados funcionais do professor
  
.. _RN1: `Regras de Negócio`_  
   
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
     - Atualização realizada com sucesso.       

.. _M1: `Mensagens`_

    
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

.. figure:: media/tela_uc211_01.png
   :align: center
   :scale: 100 %
   :alt: protótipo de tela.
   :figclass: align-center
   
   Figura 1: Protótipo de tela para edição de dados funcionais do professor.
	   
	   
.. _`Figura 2`:

.. comentário para usar o exemplo abaixo, basta recuar a margem.
	   
	.. figure:: media/tela_uc211.png
	   :align: center
	   :scale: 70 %
	   :alt: protótipo de tela.
	   :figclass: align-center
	   
	   Figura 2: Protótipo de tela para cadastro de dados funcionais do professor.	   

Diagrama de domínio do caso de uso
----------------------------------

Não há.

Diagrama de Fluxo de Operação
-----------------------------

Não há.

Cenário de Testes
-----------------

Não há.