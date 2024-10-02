
.. |logo| image:: ../../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Ensino** 

.. include:: ../../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-edu-ensino-proc_apoio-uc503: 

UC 503 - Manter Calendários Acadêmicos <v0.1>
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
   * - 06/05/2014
     - 0.1
     - Início do Documento
     - 

Objetivo
--------

.. warning:: 
   informa objetivo aqui.

Atores
------

Principais
^^^^^^^^^^

**ator**:

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

    #. O caso de uso é iniciado acionando a opção  ``ENSINO`` > ``Procedimentos de Apoio`` > ``Calendários Acadmêmicos``
    #. O sistema exibe a lista de calendários acadêmicos (RIN1_)
    #. O **ator** seleciona a opção ``Adicionar Calendário Acadêmico` 
    #. O **ator** informa os dados (RIN2_)
    #. O **ator** finaliza o caso de uso selecionando a opção ``Salvar``
    #. O sistema exibe a mensagem M1_
    #. O sistema apresenta a listagem do passo FN_.2 


Fluxo Alternativo
^^^^^^^^^^^^^^^^^

.. _FA1:

FA1 - Editar (FN_.2 )
"""""""""""""""""""""

	#. O **ator** aciona a opção ``Editar`` de uma das calendários acadêmicos disponíveis na listagem
	#. O sistema exibe a calendário academico com os dados (RIN2_) preenchidos
	#. O **ator** informa novos valores para os dados (RIN2_) 
	#. O **ator** finaliza o caso de uso selecionando a opção ``Salvar``
	#. O sistema exibe a mensagem M2_.
	#. O sistema apresenta a listagem do passo FN_.2 
	
	
FA2 - Salvar e adicionar outro(a) (FN_.4)
"""""""""""""""""""""""""""""""""""""""""

	#. O **ator** aciona a opção ``Salvar e adicionar outro(a)``
	#. O sistema exibe a mensagem M3_.
	#. O caso de uso volta para o passo FN_.4 


FA3 - Salvar e continuar editando (FA1_.3)
""""""""""""""""""""""""""""""""""""""""""

	#. O **ator** aciona a opção ``Salvar e continuar editando``
	#. O sistema exibe a mensagem M4_.
	#. O caso de uso volta para o passo F1_.3 
	

FA4 - Listar (FN_.2)
""""""""""""""""""""

	#. O **ator** restringe a lista usando o filtro e/ou busca (RIN1_)
	#. O sistema exibe uma lista que satisfaça aos critérios informados no passo anterior


FA5 - Visualizar (FN_.2)
""""""""""""""""""""""""

	#. O **ator** aciona a opção ``Ver`` da calendário academico que se deseja realizar o vínculo dentre uma das 
	   calendários acadêmicos disponíveis na listagem
	#. O sistema exibe informações da calendário academico (RI1_)


.. _FA6:
	
FA6 - Remover (FA1_.2) 
""""""""""""""""""""""

    #. O **ator** aciona a opção ``Apagar`` 
    #. O sistema exibe a mensagem M5_
    #. O **ator** aciona a opção "Sim, tenho certeza"
    #. O sistema exibe a mensagem M6_
    #. O **ator** confirma a exclusão.
    #. O sistema apresenta a listagem do passo FN_.2 
    	
    	
Fluxo de Exceção
^^^^^^^^^^^^^^^^

FE1 – Exclusão fere Regra RN1 (FA6_.1)
""""""""""""""""""""""""""""""""""""""

Especificação suplementares
---------------------------

Requisitos Não-Funcionais
^^^^^^^^^^^^^^^^^^^^^^^^^ 

Não há.

Requisitos de Interface
^^^^^^^^^^^^^^^^^^^^^^^

.. _RI1:

RI1 – Exibição da calendário academico 
""""""""""""""""""""""""""""""""""""""

Os dados da calendário academico é exibida dentro de uma caixa de nome "**nome_caixa_identificacao**", são eles:

- ``campo 1``: <campo nome_campo1>
- ``campo 2``: <campo nome_campo2>

Além da caixa "**nome_caixa_identificacao**" é exibida outras caixas, listo as logo abaixo:
- "nome_caixa_2"

  - detalhar o conteúdo dessa caixa.

- "nome_caixa_3"

  - detalhar o conteúdo dessa caixa. 

A `Figura 1`_ exibe um esboço de como esses dados serão exibidos.

Requisitos de Informação
^^^^^^^^^^^^^^^^^^^^^^^^
.. _RIN1:
     
RIN1 – Campos para listagem de calendários acadêmicos
"""""""""""""""""""""""""""""""""""""""""""""""""""""
 
A listagem é exibida dividida em abas conforme especificadas abaixo:

- ``Aba 1``: descrever o que exibido nessa aba
- ``Aba 2``: descrever o que exibido nessa aba
     
.. list-table:: 
   :header-rows: 1
   :stub-columns: 1

   * - 
     - Ações
     - Campo 1
     - Campo 2
   * - Ordenação
     - Não
     - Não
     - Não
   * - Filtro
     - Não
     - Não
     - Não
   * - Busca
     - Não
     - Não
     - Não   
   * - Observações
     - 
       .. csv-table::
          :header: "Rótulo"
          :widths: 100

          Ver
          Editar
     - 
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
   * - Campo 1*
     - ver lista de tipos em RIN2 do template :ref:`suap-artefatos-sistema-subsistema-uc01`
     - 
     - 
     - 
     - 

A `Figura 2`_ exibe um esboço do formulário de cadastro.

     
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
       | A remoção de **UC** "<campo descrição>" pode resultar na remoção de objetos relacionados, mas sua conta não tem a permissão para remoção dos seguintes tipos de objetos: 
  
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
     - **UC** <campo nome1> alterado com sucesso. Você pode adicionar um outro Diretoria Acadêmica abaixo.
   * - M4
     - **UC** <campo nome1> modificado com sucesso. Você pode editá-lo novamente abaixo.
   * - M5
     - Você tem certeza que quer remover **UC** "<campo nome1>"? Todos os seguintes itens relacionados serão removidos:    
   * - M6
     - Tem certeza que deseja continuar?       

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

	.. figure:: images/tela_uc**numero**_exibir.png
	   :align: center
	   :scale: 70 %
	   :alt: protótipo de tela.
	   :figclass: align-center
	   
	   Figura 1: Protótipo de tela para exibição de calendários acadêmicos.
	   
	   
.. _`Figura 2`:

.. comentário para usar o exemplo abaixo, basta recuar a margem.
	   
	.. figure:: images/tela_uc**numero**.png
	   :align: center
	   :scale: 70 %
	   :alt: protótipo de tela.
	   :figclass: align-center
	   
	   Figura 2: Protótipo de tela para cadastro de calendários acadêmicos.	   

Diagrama de domínio do caso de uso
----------------------------------

Não há.

Diagrama de Fluxo de Operação
-----------------------------

Não há.

Cenário de Testes
-----------------

Não há.