:orphan:

.. |logo| image:: ../../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Ensino** 

.. include:: ../../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-edu-ensino-cad_gerais-uc124:

UC 124 - Manter tipos de atividades complementares  <v0.1>
==========================================================

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
   * - 19/07/2014
     - 0.1
     - Início do Documento
     - Jailton Carlos
   * - 29/07/2014
     - 0.2
     - Alteração de atividade extracurricular para atividade complementar
     - Jailton Carlos
     
     
Objetivo
--------

Este caso de uso permite cadastrar, alterar, remove ou listar tipos de atividades complementares.

Uma tipo de atividade complementar será utilizado ao lançar uma atividade complementar do aluno e ao 
vincular atividade a configuração de AACC.

Atores
------

Principais
^^^^^^^^^^

Administrador: permite gerir o cadastro de tipos de atividades complementares. 

Interessado
^^^^^^^^^^^

Não se aplica.

Pré-condições
-------------



Pós-condições
-------------



Fluxo de Eventos
----------------

Fluxo Normal
^^^^^^^^^^^^

.. _FN:

    #. O caso de uso é iniciado acionando a opção  ``ENSINO`` > ``Cadastros Gerais`` > ``Tipos de Atividade Complementar``
    #. O sistema exibe a lista de tipos de atividades complementares (RIN1_)
    #. O administrador seleciona a opção ``Adicionar Tipo de Atividade complementar``
    #. O administrador informa os dados (RIN2_)
    #. O administrador finaliza o caso de uso selecionando a opção ``Salvar``
    #. O sistema exibe a mensagem M1_
    #. O sistema apresenta a listagem do passo FN_.2 

Fluxo Alternativo
^^^^^^^^^^^^^^^^^

.. _FA1:

FA1 – Editar (FN_.2 )
"""""""""""""""""""""

	#. O administrador aciona a opção ``Editar`` dentre uma das tipos de atividades complementares disponíveis na listagem
	#. O sistema exibe o tipo de atividade complementar com os dados (RIN2_) preenchidos
	#. O administrador informa novos valores para os dados (RIN2_) 
	#. O administrador finaliza o caso de uso selecionando a opção ``Salvar``
	#. O sistema exibe a mensagem M2_.
	#. O sistema apresenta a listagem do passo FN_.2 
	
FA2 - Salvar e adicionar outro(a) (FN_.4)
"""""""""""""""""""""""""""""""""""""""""

	#. O administrador aciona a opção ``Salvar e adicionar outro(a)``
	#. O sistema exibe a mensagem M3_.
	#. O caso de uso volta para o passo FN_.4

.. _FA3:

FA3 - Salvar e continuar editando (FA1_.3)
""""""""""""""""""""""""""""""""""""""""""

	#. O administrador aciona a opção ``Salvar e continuar editando``
	#. O sistema exibe a mensagem M4_.
	#. O caso de uso volta para o passo FA1_.3
	

FA4 – Listar (FN_.2)
""""""""""""""""""""

	#. O administrador restringe a lista usando o filtro e/ou busca (RIN1_)
	#. O sistema exibe uma lista que satisfaça aos critérios informados no passo anterior

.. _FA5:   

FA5 - Remover (FA1_.2)
""""""""""""""""""""""

    #. O administrador aciona a opção ``Apagar`` 
    #. O sistema exibe a mensagem M5_
    #. O administrador aciona a opção "Sim, tenho certeza"
    #. O sistema exibe a mensagem M6_
    #. O administrador confirma a exclusão.
    #. O caso de uso volta para o passo FN_.2


Fluxo de Exceção
^^^^^^^^^^^^^^^^

FE1 – Exclusão fere Regra RN1_ (FA5_-1)
"""""""""""""""""""""""""""""""""""""""

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
     
RIN1 – Campos para listagem de atividade
""""""""""""""""""""""""""""""""""""""""

.. list-table:: 
   :header-rows: 1
   :stub-columns: 1

   * - 
     - Ações
     - Descrição
   * - Ordenação
     - Não
     - Sim
   * - Filtro
     - Não
     - Não
   * - Busca
     - Não
     - Sim   
   * - Observações
     - 
       .. csv-table::
          :header: "Rótulo"
          :widths: 100

          Editar
     - 


.. _RIN2:


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
     - Domínio/Máscara
     - Observação
   * - Descrição*
     - Texto
     - 
     - 
     - 
     - 
     
     
Regras de Negócio
^^^^^^^^^^^^^^^^^

.. list-table:: 
   :widths: 10 90
   :header-rows: 1
   :stub-columns: 0

   * - Regra
     - Descrição / Mensagem
   * - RN1
     - | Exclusão fere integridade relacional.
       | A remoção de atividade complementar "<campo Descrição>" pode resultar na remoção de objetos relacionados, mas sua conta não tem a permissão para remoção dos seguintes tipos de objetos: 
   
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
     - Cadastro realizado com sucesso.
   * - M2
     - Atualização realizada com sucesso.
   * - M3
     - atividade complementar "<campo Descrição>" alterado com sucesso. Você pode adicionar um outro atividade complementar abaixo.
   * - M4
     - atividade complementar "<campo Descrição>" modificado com sucesso. Você pode editá-lo novamente abaixo. 
   * - M5
     - Você tem certeza que quer remover atividade complementar "<campo Descrição>"? Todos os seguintes itens relacionados serão removidos:    

.. _M1: `Mensagens`_     
.. _M2: `Mensagens`_
.. _M3: `Mensagens`_    
.. _M4: `Mensagens`_   
.. _M5: `Mensagens`_    

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