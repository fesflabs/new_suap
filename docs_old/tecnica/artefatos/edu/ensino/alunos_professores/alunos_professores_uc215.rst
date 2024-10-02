
.. |logo| image:: ../../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Ensino** 

.. include:: ../../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-edu-ensino-alunos_professores-uc215:

UC 215 - Visualizar Boletim <v0.1>
=======================================

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
   * - 11/07/2014
     - 0.1
     - Início do Documento
     - Ibanêz Cavalcanti Ferreira

Objetivo
--------

Permite aos usuários visualizar o boletim do aluno.

Atores
------

Principais
^^^^^^^^^^

Administradores do sistema, Diretores, Coordenadores, Pedagogos e Secretários.

Interessado
^^^^^^^^^^^

Não se aplica.

Pré-condições
-------------

Aluno cadastrado no sistema.

Pós-condições
-------------

Não se aplica.

Casos de Uso Impactados
-----------------------

Não se aplica.

Fluxo de Eventos
----------------

Fluxo Normal
^^^^^^^^^^^^

.. _FN:

    #. O caso de uso é iniciado a partir do passo FN.2 do caso de uso :ref:`suap-artefatos-edu-ensino-alunos_professores-uc202`, ao 
       acionar a  opção ``ENSINO`` > ``Alunos e Professores`` > ``Alunos``,  em seguida, selecionando a opção ``Ver``
       do aluno dentre um dos alunos disponíveis na listagem, depois acionar a aba ``Visualizar boletim``
    #. O sistema muda de aba exibindo o ``Boletim``.


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
     
RIN1 – Campos para listagem neste caso de uso
""""""""""""""""""""""""""""""""""""""""""""""""""

     
.. list-table:: 
   :widths: 5 5 5 5 5 5
   :header-rows: 1
   :stub-columns: 0

   * - Informação
     - Tipo
     - Tamanho
     - Valor Inicial
     - Domínio/Máscara
     - Observação
   * - Diário
     - Inteiro
     - 
     - 
     - 
     - Se secretário, link para diário. Se aluno, link para sala virtual.
   * - Turma
     - Texto
     - 
     - 
     - 
     - Se secretário, link para turma. Se aluno texto.
   * - Descrição da Disciplina
     - Texto
     - 
     - 
     - 
     -      
   * - Carga Horária Relógio
     - Inteiro
     - 
     - 
     - 
     - 
   * - Quantidade de Aulas Ministradas
     - Inteiro
     - 
     - 
     - 
     -  
   * - Situação do Aluno na Disciplina
     - Texto
     - 
     - 
     - 
     -       
   * - Notas das Etapas
     - Inteiro
     - 
     - 
     - 
     -       
   * - Faltas das Etapas
     - Inteiro
     - 
     - 
     - 
     -       
   * - Nota da Avaliação Final(NAF)
     - Inteiro
     - 
     - 
     - 
     -       
   * - Média da Disciplina(MD)
     - Inteiro
     - 
     - 
     - 
     -       
   * - Média Final da Disciplina(MDF)
     - Inteiro
     - 
     - 
     - 
     -       

            

.. _RIN2:

RIN2 – Campos para Cadastros
""""""""""""""""""""""""""""

Não há.

     
Regras de Negócio
^^^^^^^^^^^^^^^^^

Não há.
   
Mensagens
^^^^^^^^^

Não há.

    
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


	.. figure:: media/tela_uc215_visualizar_boletim.png
	   :align: center
	   :scale: 100 %
	   :alt: protótipo de tela.
	   :figclass: align-center
	   
	   Figura 1: Protótipo de tela para exibição do boletim.
	   

Diagrama de domínio do caso de uso
----------------------------------

Não há.

Diagrama de Fluxo de Operação
-----------------------------

Não há.

Cenário de Testes
-----------------

Não há.