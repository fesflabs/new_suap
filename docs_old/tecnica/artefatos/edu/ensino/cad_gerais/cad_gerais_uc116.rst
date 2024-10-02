
.. |logo| image:: ../../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Ensino** 

.. include:: ../../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-edu-ensino-cad_gerais-uc116:

UC 116 - Vincular Diretor Geral <v0.1>
======================================

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

Caso de uso extensor que possibilitar vincular um diretor geral a uma Diretoria.

Atores
------ 

Principais
^^^^^^^^^^

Administrador: associa um diretor geral a uma diretoria.

Interessado
^^^^^^^^^^^

Não há.

Pré-condições
-------------

Deve existir ao menos um servidor ativo.

Pós-condições
-------------

Nome do diretor geral títular será impresso no diploma ou certificado de curso dependendo do modelo de documento adotado.

Fluxo de Eventos
----------------

Fluxo Normal
^^^^^^^^^^^^

.. _FN:

    #. O caso de uso é iniciado a partir do passo FA3.2 do caso de uso :ref:`suap-artefatos-edu-ensino-cad_gerais-uc114`, ao 
       acionar a  opção ``ENSINO`` > ``Cadastros Gerais`` > ``Diretorias Acadêmicas``,  em seguida, selecionando a opção ``Ver`` 
       da diretoria acadêmica que se deseja realizar o vínculo dentre uma das diretorias acadêmicas disponíveis na listagem
    #. O sistema exibe informações da diretoria acadêmica (ver RI1 do caso de uso :ref:`suap-artefatos-edu-ensino-cad_gerais-uc114`)
    #. O administrador seleciona a opção ``Adicionar Diretor Geral`` 
    #. O administrador seleciona o servidor (RIN1_)
    #. O administrador finaliza o caso de uso selecionando a opção ``Vincular``
    #. O caso de uso retorna para o passo do FN.2 

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

RIN1 – Campos para Cadastros
""""""""""""""""""""""""""""

.. list-table:: 
   :widths: 10 20 5 5 5 5
   :header-rows: 1
   :stub-columns: 0

   * - Informação
     - Tipo
     - Tamanho
     - Valor Inicial
     - Domínio/Máscara
     - Observação
   * - Setor*
     - Usuário (texto auto-completar simples)
     - 
     - 
     - 
     - 
     
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