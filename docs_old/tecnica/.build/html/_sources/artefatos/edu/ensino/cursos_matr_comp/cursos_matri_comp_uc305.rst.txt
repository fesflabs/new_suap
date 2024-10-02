
.. |logo| image:: ../../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Ensino** 

.. include:: ../../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-edu-ensino-cursos_matr_comp-uc305: 

UC 305 - Vincular matriz ao curso <v0.1>
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
   * - 22/04/2014
     - 0.1
     - Início do Documento
     - Jailton Carlos
   * - 21/07/2014
     - 0.2
     - Edição do Documento
     - Ibanez Ferreira

Objetivo
--------

Caso de uso extensor que possibilitar vincular uma matriz ao curso.

Atores
------ 

Principais
^^^^^^^^^^

Administrador: associa uma matriz curricular a um curso.

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

    #. O caso de uso é iniciado a partir do passo FA6.3 do caso de uso :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc304`, ao 
       acionar a  opção ``ENSINO`` > ``Cursos, Matrizes e Componentes`` > ``Cursos``, em seguida, selecionando a opção ``Ver`` 
       do curso que se deseja realizar o vínculo dentre um dos cursosdisponíveis na listagem
    #. O sistema exibe informações das matrizes vinculadas na caixa "Matrizes" (ver RI1 do caso de uso :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc304`)
    #. O administrador seleciona a opção ``Vincular Matriz`` 
    #. O administrador informar os dados (RIN1_)
    #. O administrador finaliza o caso de uso selecionando a opção ``Salvar``
    #. O caso de uso retorna para o passo do FN.2 

Fluxo Alternativo
^^^^^^^^^^^^^^^^^

Não há
	
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

.. list-table:: 
   :widths: 10 5 5 5 5 20
   :header-rows: 1
   :stub-columns: 0

   * - Informação
     - Tipo
     - Tamanho
     - Valor Inicial
     - Domínio/Máscara
     - Observação
   * - Matriz
     - Objeto
     - 
     - 
     - 
     - Será escolhida uma matriz para estar associada ao curso.
   
     
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

. _`Figura 1`:


    .. figure:: media/uc305.png
       :align: center
       :scale: 100 %
       :alt: protótipo de tela.
       :figclass: align-center
       
       Figura 1: Protótipo de tela para vincular uma matriz a um curso.


Diagrama de domínio do caso de uso
----------------------------------

Não há.

Diagrama de Fluxo de Operação
-----------------------------

Não há.

Cenário de Testes
-----------------

Não há.