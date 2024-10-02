
.. |logo| image:: ../../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Ensino** 

.. include:: ../../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-edu-ensino-cursos_matr_comp-uc303: 

UC 303 - Vincular componente à matriz <v0.1>
=============================================

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
   * - 22/04/2014
     - 0.1
     - Início do Documento
     - Jailton Carlos

Objetivo
--------

Caso de uso extensor que possibilitar vincular um componente a uma matriz curricular.

Atores
------ 

Principais
^^^^^^^^^^

Administrador: associa um componente a uma matriz curricular.

Interessado
^^^^^^^^^^^

Não há.

Pré-condições
-------------



Pós-condições
-------------



Fluxo de Eventos
----------------

Fluxo Normal
^^^^^^^^^^^^

.. _FN:

    #. O caso de uso é iniciado a partir do passo FA6.3 do caso de uso :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc302`, ao 
       acionar a  opção ``ENSINO`` > ``Cursos, Matrizes e Componentes`` > ``Matrizes Curriculares``, em seguida, selecionando a opção ``Ver`` 
       da matriz curricular que se deseja realizar o vínculo dentre uma das matrizes curriculares disponíveis na listagem, depois
       selecionar a aba ``Componentes Curriculares``
    #. O sistema exibe informações dos componentes curriculares vinculados (ver RI1 do caso de uso :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc302`)
    #. O administrador seleciona a opção ``Vincular Componente`` 
    #. O administrador informar os dados (RIN1_)
    #. O administrador finaliza o caso de uso selecionando a opção ``Vincular Componente``
    #. O caso de uso retorna para o passo do FN.2 

Fluxo Alternativo
^^^^^^^^^^^^^^^^^

.. _FA1:

FA1 – Vincular componente e continuar vinculando (FN_.4 )
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""

	#. O administrador aciona a opção ``Vincular componente e continuar vinculando`` 
	#. O caso de uso retorna para o passo FN_.4


FA2 – Editar Vínculo (FN_.4 )
"""""""""""""""""""""""""""""

    #. O caso de uso é iniciado a partir do passo FA6.3 do caso de uso :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc302`, ao 
       acionar a  opção ``ENSINO`` > ``Cursos, Matrizes e Componentes`` > ``Matrizes Curriculares``, em seguida, selecionando a opção ``Ver`` 
       da matriz curricular que se deseja realizar o vínculo dentre uma das matrizes curriculares disponíveis na listagem, depois
       selecionar a aba ``Componentes Curriculares``
    #. O sistema exibe informações dos componentes curriculares vinculados (ver RI1 do caso de uso :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc302`)
    #. O administrador seleciona a opção ``Editar Vínculo`` 
    #. O sistema exibe a os dados (RIN1_) do vínculo preenchidos
    #. O administrador informa novos valores para os dados (RIN1_) 
    #. O administrador finaliza o caso de uso selecionando a opção ``Vincular Componente``
    #. O caso de uso retorna para o passo do FN.2 
	
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

RIN1 – Campos para Cadastros
""""""""""""""""""""""""""""

     
Regras de Negócio
^^^^^^^^^^^^^^^^^

Não há.
   
Mensagens
^^^^^^^^^

Não há.
     
Ponto de Extensão
-----------------

Não há.

Questões em Aberto
------------------

Não há.

Esboço de Protótipo 
-------------------

Não há.

Diagrama de domínio do caso de uso
----------------------------------

Não há.

Diagrama de Fluxo de Operação
-----------------------------

Não há.

Cenário de Testes
-----------------

Não há.