
.. |logo| image:: ../../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Ensino** 

.. include:: ../../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-edu-ensino-alunos_professores-uc200: 

UC 200 - Visualizar Histórico <v0.1>
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
     - Jailton Carlos

Objetivo
--------

Exibir o histórico escolar do aluno.

Atores
------

Principais
^^^^^^^^^^

Secretário, Diretor Acadêmico, Administrador

Interessado
^^^^^^^^^^^

Não se aplica.

Pré-condições
-------------

Pós-condições
-------------

Casos de Uso Impactados
-----------------------

Não há.

Fluxo de Eventos
----------------

Fluxo Normal
^^^^^^^^^^^^

.. _FN:


    #. O caso de uso é iniciado a partir do passo FA5.2 do caso de uso :ref:`suap-artefatos-edu-ensino-alunos_professores-uc202`, ao 
       acionar a  opção ``ENSINO`` > ``Alunos e Professores`` > ``Alunos``,  em seguida, selecionando a opção ``Ver`` 
       do aluno dentre um dos alunos disponíveis na listagem
    #. O secretário aciona a opção ``Histórico`` 
    #. O sistema exibe o histórico (RIN1_)


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

RIN1 – Campos para listagem do Histórico
""""""""""""""""""""""""""""""""""""""""
     
.. list-table:: 
   :header-rows: 1
   :stub-columns: 1

   * - 
     - Período Letivo
     - Período
     - Diário
     - Código
     - Componente Curricular
     - C. H.
     - Faltas
     - Nota
     - Situação
     - Ações
   * - Ordenação   
     - Não
     - Sim
     - Não
     - Não
     - Sim
     - Não
     - Não
     - Não
     - Não
     - Não   
   * - Filtro
     - Não
     - Não
     - Não
     - Não
     - Não
     - Não
     - Não
     - Não
     - Não
     - Não   
   * - Busca
     - Não
     - Não
     - Não
     - Não
     - Não
     - Não
     - Não
     - Não
     - Não
     - Não   
   * - Observações
     - Não
     - Não
     - Não
     - Não
     - Não
     - Não
     - Não
     - Não
     - Não
     - 
       .. csv-table::
          :header: "Ações"
          :widths: 100

          Conforme `Ponto de Extensão`_
     
A `Figura 1`_ exibe um esboço do formulário de cadastro.


Regras de Negócio
^^^^^^^^^^^^^^^^^

Não há.
   
Mensagens
^^^^^^^^^

Não há.
    
.. _PE:

Ponto de Extensão
-----------------

	#. :ref:`suap-artefatos-edu-ensino-alunos_professores-uc203` 

Questões em Aberto
------------------

Não há.

Esboço de Protótipo
-------------------

.. _`Figura 1`:


	.. figure:: media/tela_uc200.png
	   :align: center
	   :scale: 100 %
	   :alt: protótipo de tela.
	   :figclass: align-center
	   
	   Figura 1: Protótipo de tela para exibição do histórico.


Diagrama de domínio do caso de uso
----------------------------------

Não há.

Diagrama de Fluxo de Operação
-----------------------------

Não há.

Cenário de Testes
-----------------

Não há.