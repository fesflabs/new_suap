
.. |logo| image:: ../../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Ensino** 

.. include:: ../../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-edu-ensino-alunos_professores-uc209: 

UC 209 - Editar Foto do Professor <v0.1>
========================================

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
     - Hugo Tácito Azevedo de Sena

Objetivo
--------

Altera a foto do professor.

Atores
------

Principais
^^^^^^^^^^

Secretário, Administrador, Coordenador, Diretor Geral e Acadêmico: podem alterar a foto do professor.

Interessado
^^^^^^^^^^^

Professor.

Pré-condições
-------------

O professor precisa estar cadastrado.

Pós-condições
-------------

O professor tem sua foto alterada.

Casos de Uso Impactados
-----------------------

	#. :ref:`suap-artefatos-edu-ensino-alunos_professores-uc208` - Altera a foto do professor.

Fluxo de Eventos
----------------

Fluxo Normal
^^^^^^^^^^^^

.. _FN:

    #. O caso de uso é iniciado acionando a opção  ``ENSINO`` > ``Alunos e Professores`` > ``Professores``
    #. O sistema exibe a lista de professores (:ref:`suap-artefatos-edu-ensino-alunos_professores-uc208-RIN1`)
    #. O Secretário seleciona um professor.
    #. O sistema exibe os dados gerais do professor.
    #. O Secretário seleciona a opção de edição de foto.
    #. O sistema exibe o formulário de edição de foto.
    #. O Secretário seleciona a nova foto e clica na opção ``Salvar``.
    #. O sistema exibe a mensagem M1_. 


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

Não há

Requisitos de Informação
^^^^^^^^^^^^^^^^^^^^^^^^

.. _RIN1:
     
RIN1 – Campos para Edição de Foto de Professor
""""""""""""""""""""""""""""""""""""""""""""""

.. list-table:: 
   :widths: 10 10 5 5 5 15
   :header-rows: 1
   :stub-columns: 0

   * - Informação
     - Tipo
     - Tamanho
     - Valor Inicial
     - Domínio/Máscara
     - Observação
   * - Captura de foto com a câmera
     - Arquivo
     - 
     - 
     - Imagem
     - A imagem é capturada em flash
   * - Upload de arquivo
     - Arquivo
     - 
     - 
     - Imagem
     - 

A `Figura 1`_ exibe um esboço do formulário de edição de foto.
     
Regras de Negócio
^^^^^^^^^^^^^^^^^

.. list-table:: 
   :widths: 10 90
   :header-rows: 1
   :stub-columns: 0

   * - Regra
     - Descrição / Mensagem
   * - RN1
     - | O envio de pelo menos um tipo de foto é obrigatório (Câmera ou arquivo).
       | mensagem : M2_
  
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
     - Foto atualizada com sucesso.
   * - M2
     - Retire a foto com a câmera ou forneça um arquivo.   

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

.. figure:: media/tela_uc209_01.png
   :align: center
   :scale: 100 %
   :alt: protótipo de tela.
   :figclass: align-center
   
   Figura 1: Protótipo de tela para Editar a Foto do Professor.
	   
	   
.. _`Figura 2`:

.. comentário para usar o exemplo abaixo, basta recuar a margem.
	   
	.. figure:: media/tela_uc209.png
	   :align: center
	   :scale: 70 %
	   :alt: protótipo de tela.
	   :figclass: align-center
	   
	   Figura 2: Protótipo de tela para cadastro de Foto de Professor.	   

Diagrama de domínio do caso de uso
----------------------------------

Não há.

Diagrama de Fluxo de Operação
-----------------------------

Não há.

Cenário de Testes
-----------------

Não há.