
.. |logo| image:: ../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Comum** 

.. include:: ../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-adm-agendamento_salas-uc01: 

UC 01- Manter Salas <v0.1>
==========================

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
   * - 08/05/2014
     - 0.1
     - Início do Documento
     - Jailton Carlos
     
.. comentário
   08/05 - início do documento


Objetivo
--------

Cadastrar, alterar ou listar Salas.

Atores
------

Principais
^^^^^^^^^^

Operador de chaves (chaves_operador): responsável por manter o cadastro de salas, indicar quais estão 
disponíveis para agendamento e quais são seus avaliadores.

Interessado
^^^^^^^^^^^

Servidor que faz uso da sala para solicitar reservas.

Pré-condições
-------------

Não há.

Pós-condições
-------------

Não há.

Fluxo de Eventos
----------------

Fluxo Normal
^^^^^^^^^^^^

.. _FN:

    #. O caso de uso é iniciado acionando a opção  ``ADMINISTRAÇÃO`` > ``Cadastros`` > ``Salas``
    #. O sistema exibe a lista de Salas (RIN1_)
    #. O operador de chaves seleciona a opção ``Adicionar Sala`` 
    #. O operador de chaves informa os dados (RIN2_)
    #. O operador de chaves finaliza o caso de uso selecionando a opção ``Salvar``
    #. O sistema exibe a mensagem M1_
    #. O sistema apresenta a listagem do passo FN_.2 


Fluxo Alternativo
^^^^^^^^^^^^^^^^^

.. _FA1:

FA1 - Editar (FN_.2 )
"""""""""""""""""""""

	#. O operador de chaves aciona a opção ``Editar`` de uma das Salas disponíveis na listagem
	#. O sistema exibe a sala com os dados (RIN2_) preenchidos
	#. O operador de chaves informa novos valores para os dados (RIN2_) 
	#. O operador de chaves finaliza o caso de uso selecionando a opção ``Salvar``
	#. O sistema exibe a mensagem M2_.
	#. O sistema apresenta a listagem do passo FN_.2 
	
	
FA2 - Salvar e adicionar outro(a) (FN_.4)
"""""""""""""""""""""""""""""""""""""""""

	#. O operador de chaves aciona a opção ``Salvar e adicionar outro(a)``
	#. O sistema exibe a mensagem M3_.
	#. O caso de uso volta para o passo FN_.4 


FA3 - Salvar e continuar editando (FA1_.3)
""""""""""""""""""""""""""""""""""""""""""

	#. O operador de chaves aciona a opção ``Salvar e continuar editando``
	#. O sistema exibe a mensagem M4_.
	#. O caso de uso volta para o passo F1_.3 
	

FA4 - Listar (FN_.2)
""""""""""""""""""""

	#. O operador de chaves restringe a lista usando o filtro e/ou busca (RIN1_)
	#. O sistema exibe uma lista que satisfaça aos critérios informados no passo anterior

    	
Fluxo de Exceção
^^^^^^^^^^^^^^^^

FE1 – Salvamento/Edição fere Regra RN1_ (FN_.4 e FA1_.3)
""""""""""""""""""""""""""""""""""""""""""""""""""""""""

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

.. _suap-artefatos-adm-agendamento_salas-uc01-rin1:
     
RIN1 – Campos para listagem de Salas
""""""""""""""""""""""""""""""""""""     
     
.. list-table:: 
   :widths: 20 10 10 10 10 10 30
   :header-rows: 1
   :stub-columns: 1

   * - 
     - Ações
     - Nome
     - Prédio
     - Setores
     - Ativa
     - Agendável
   * - Ordenação
     - Não
     - Sim
     - Sim
     - Não
     - Não
     - Não
   * - Filtro
     - Não
     - Não
     - Sim
     - Não
     - Não
     - Sim
     
       .. note::
          | Domíno: Todos, Sim e Não.
          | Padrão: Sim.
   * - Busca
     - Não
     - Sim
     - Não
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
     -
     -
     - RN2_
     
       .. csv-table::
          :header: "Botão"
          :widths: 100

          Solicitar Reserva
          

.. _RIN2:

RIN2 – Campos para Cadastros
""""""""""""""""""""""""""""

.. list-table:: 
   :widths: 20 30 5 5 5 35
   :header-rows: 1
   :stub-columns: 0

   * - Informação
     - Tipo
     - Tamanho
     - Valor Inicial
     - Domínio/Máscara
     - Observação
   * - Nome*
     - Texto
     - 
     - 
     - 
     - 
   * - Ativa
     - Caixa de checagem
     - 
     - 
     - 
     - 
   * - Prédio*
     - Seleção
     - 
     - 
     - 
     - Inlcuir atalho para adicionar novos prédios
   * - Setores
     - Texto autocompletar multiplo
     - 
     - 
     - 
     - 
   * - Agendável
     - Caixa de checagem
     - 
     - 
     - 
     - 
   * - Capacidade da sala
     - 
     - 
     - 
     - 
     - Dica: número máximo de pessoas
   * - Avaliadores de agendamento
     - Texto autocompletar multiplo
     - 
     - 
     - 
     - RN1_


A `Figura 1`_ exibe um esboço do formulário de cadastro.


.. _suap-artefatos-adm-agendamento_salas-uc01-rn1:      
     
Regras de Negócio
^^^^^^^^^^^^^^^^^

.. list-table:: 
   :widths: 10 90
   :header-rows: 1
   :stub-columns: 0

   * - Regra
     - Descrição / Mensagem
   * - RN1
     - | Se o campo "Agendável" estiver marcado, o campo "Avaliadores de agendamento" torna-se obrigatório.
       | mensagem: "Você informou que a sala é agendável, sendo assim, esté campo torna-se obrigatório. 
   * - RN2
     - | Critério para exibição do botão "Solicitar Reserva": sala deve está ativa, disponível para agendamento e deve ter ao menos um avaliador de agendamento.
       | mensagem: Não ha. 
       

.. _RN1: `Regras de Negócio`_   
.. _RN2: `Regras de Negócio`_   
   
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
     - Sala <campo nome> - <campo predio> alterado com sucesso. Você pode adicionar um outro Diretoria Acadêmica abaixo.
   * - M4
     - Sala <campo nome> - <campo predio>  modificado com sucesso. Você pode editá-lo novamente abaixo.   

.. _M1: `Mensagens`_     
.. _M2: `Mensagens`_
.. _M3: `Mensagens`_    
.. _M4: `Mensagens`_    

    
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

.. figure:: media/manter_sala.png
   :align: center
   :scale: 70 %
   :alt: protótipo de tela.
   :figclass: align-center
   
   Figura 2: Protótipo de tela para cadastro de Salas.	   

Diagrama de domínio do caso de uso
----------------------------------

Não há.

Diagrama de Fluxo de Operação
-----------------------------

Não há.

Cenário de Testes
-----------------

Não há.